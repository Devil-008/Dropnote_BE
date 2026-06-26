from datetime import datetime
import uuid
from .. import db

class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    mime_type = db.Column(db.String(127))
    size_bytes = db.Column(db.BigInteger, nullable=False)
    checksum_sha256 = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shares = db.relationship('FileShare', backref='file', cascade='all, delete-orphan')

class FileShare(db.Model):
    __tablename__ = 'file_shares'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = db.Column(db.String(36), db.ForeignKey('files.id', ondelete='CASCADE'), nullable=False)
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime)
    max_downloads = db.Column(db.Integer)
    download_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    qr_codes = db.relationship('QRCode', backref='share', cascade='all, delete-orphan')
    download_logs = db.relationship('DownloadLog', backref='share', cascade='all, delete-orphan')

class QRCode(db.Model):
    __tablename__ = 'qr_codes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_id = db.Column(db.String(36), db.ForeignKey('file_shares.id', ondelete='CASCADE'), nullable=False)
    qr_data = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DownloadLog(db.Model):
    __tablename__ = 'download_logs'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    share_id = db.Column(db.String(36), db.ForeignKey('file_shares.id', ondelete='CASCADE'), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
