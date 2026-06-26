from datetime import datetime
from .. import db

class CleanupJob(db.Model):
    __tablename__ = 'cleanup_jobs'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    job_type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED'), default='PENDING')
    items_processed = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    action = db.Column(db.String(127), nullable=False)
    resource_type = db.Column(db.String(64))
    resource_id = db.Column(db.String(64))
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
