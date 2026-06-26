import os
import uuid
import hashlib
import bcrypt
import qrcode
import io
import random
from datetime import datetime, timedelta
from flask import current_app
from .. import db
from ..models import File, FileShare, QRCode

class FileService:
    @staticmethod
    def initialize_upload(original_name, size_bytes, mime_type=None):
        file_id = str(uuid.uuid4())
        now = datetime.utcnow()
        relative_dir = os.path.join(
            now.strftime('%Y'),
            now.strftime('%m'),
            now.strftime('%d'),
            file_id
        )
        storage_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_dir)
        os.makedirs(storage_path, exist_ok=True)
        
        new_file = File(
            id=file_id,
            original_name=original_name,
            storage_path=relative_dir,
            size_bytes=size_bytes,
            mime_type=mime_type
        )
        db.session.add(new_file)
        db.session.commit()
        return new_file

    @staticmethod
    def save_chunk(file_id, chunk_index, chunk_data):
        file_record = File.query.get(file_id)
        if not file_record:
            return False, "File not found"
        
        chunk_filename = f"chunk_{chunk_index}"
        chunk_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.storage_path, chunk_filename)
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        
        return True, "Chunk saved"

    @staticmethod
    def finalize_upload(file_id, total_chunks):
        file_record = File.query.get(file_id)
        if not file_record:
            return False, "File not found"
        
        base_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.storage_path)
        final_file_path = os.path.join(base_path, "original_file")
        
        with open(final_file_path, 'wb') as final_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(base_path, f"chunk_{i}")
                if not os.path.exists(chunk_path):
                    return False, f"Chunk {i} missing"
                with open(chunk_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
                os.remove(chunk_path) # Clean up chunk
        
        # Calculate hash
        sha256_hash = hashlib.sha256()
        with open(final_file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        file_record.checksum_sha256 = sha256_hash.hexdigest()
        db.session.commit()
        
        return True, file_record

    @staticmethod
    def create_share(file_id, expires_in_minutes=10, password=None, max_downloads=None):
        # Enforce max 10 minutes duration
        expires_in_minutes = min(expires_in_minutes, 10)
        
        share_token = None
        while True:
            # Generate a 6-digit numeric code
            potential_token = str(random.randint(100000, 999999))
            # Check if this token already exists
            existing_share = FileShare.query.filter_by(share_token=potential_token).first()
            if not existing_share:
                share_token = potential_token
                break
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        password_hash = None
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_share = FileShare(
            file_id=file_id,
            share_token=share_token,
            password_hash=password_hash,
            expires_at=expires_at,
            max_downloads=max_downloads
        )
        db.session.add(new_share)
        db.session.commit()
        
        # Schedule auto-deletion at exact expiry time
        try:
            from ..tasks.cleanup import delete_share_task
            delete_share_task.apply_async((new_share.id,), eta=expires_at)
        except Exception as e:
            print(f"Warning: Could not schedule delete_share_task. Celery/Redis might be down. Error: {e}")
            
        # Generate QR Code pointing to the share page
        # The frontend will handle the "auto-download" logic if no password is set
        base_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        share_url = f"{base_url}/s/{share_token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes')
        os.makedirs(qr_dir, exist_ok=True)
        qr_filename = f"{share_token}.png"
        qr_path = os.path.join(qr_dir, qr_filename)
        img.save(qr_path)
        
        new_qr = QRCode(
            share_id=new_share.id,
            qr_data=share_url,
            image_path=os.path.join('qrcodes', qr_filename)
        )
        db.session.add(new_qr)
        db.session.commit()
        
        return new_share

    @staticmethod
    def get_share_by_token(token):
        return FileShare.query.filter_by(share_token=token, is_active=True).first()

    @staticmethod
    def validate_password(share, password):
        if not share.password_hash:
            return True
        if not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), share.password_hash.encode('utf-8'))
