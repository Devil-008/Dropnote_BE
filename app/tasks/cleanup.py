import os
import shutil
from datetime import datetime
from flask import current_app
from .. import celery, db
from ..models import FileShare, File, CleanupJob

@celery.task
def delete_share_task(share_id):
    share = db.session.get(FileShare, share_id)
    if not share or not share.is_active:
        return "Share not found or already inactive"
    
    file_record = share.file
    if file_record:
        # Physical path
        base_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.storage_path)
        if os.path.exists(base_path):
            shutil.rmtree(base_path, ignore_errors=True)
            
        # Optional: delete the associated QR code file if we want to be thorough
        # Since it's in qrcodes/, we'd need to delete f"{share.share_token}.png"
        qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', f"{share.share_token}.png")
        if os.path.exists(qr_path):
            os.remove(qr_path)
            
        # Delete file record from DB (which will cascade delete the share, qr code, and logs)
        db.session.delete(file_record)
        db.session.commit()
        return f"Deleted share {share_id} and physical files."
    
    return "File record not found."

@celery.task
def cleanup_expired_shares():
    now = datetime.utcnow()
    expired_shares = FileShare.query.filter(FileShare.expires_at < now, FileShare.is_active == True).all()
    
    job = CleanupJob(job_type="expired_shares_cleanup", started_at=now)
    db.session.add(job)
    db.session.commit()
    
    count = 0
    for share in expired_shares:
        # Call the task synchronously or just inline the logic to delete physically
        file_record = share.file
        if file_record:
            base_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.storage_path)
            if os.path.exists(base_path):
                shutil.rmtree(base_path, ignore_errors=True)
            
            qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', f"{share.share_token}.png")
            if os.path.exists(qr_path):
                os.remove(qr_path)
            
            db.session.delete(file_record)
        count += 1
        
    job.status = "COMPLETED"
    job.items_processed = count
    job.finished_at = datetime.utcnow()
    db.session.commit()
    return f"Cleaned up {count} shares"

@celery.task
def virus_scan_file(file_id):
    # Integration with ClamAV
    # This requires clamd to be running on the host
    import clamd
    
    file_record = File.query.get(file_id)
    if not file_record:
        return "File not found"
        
    file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], 
        file_record.storage_path, 
        "original_file"
    )
    
    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.scan(file_path)
        # Result format: {'/path/to/file': ('FOUND', 'VirusName')} or {'/path/to/file': 'OK'}
        
        status = result.get(file_path)
        if status == 'OK':
            return "Clean"
        else:
            # Infected!
            # Delete file and shares
            shutil.rmtree(os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.storage_path))
            db.session.delete(file_record)
            db.session.commit()
            return f"Infected: {status}"
    except Exception as e:
        return f"Scan failed: {str(e)}"
