from datetime import datetime
import uuid
from .. import db

class Note(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255))
    content = db.Column(db.JSON)
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = db.relationship('NoteSession', backref='note', cascade='all, delete-orphan')
    presence = db.relationship('NotePresence', backref='note', cascade='all, delete-orphan')

class NoteSession(db.Model):
    __tablename__ = 'note_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    note_id = db.Column(db.String(36), db.ForeignKey('notes.id', ondelete='CASCADE'), nullable=False)
    session_token = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotePresence(db.Model):
    __tablename__ = 'note_presence'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    note_id = db.Column(db.String(36), db.ForeignKey('notes.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.String(64))
    cursor_position = db.Column(db.Integer, default=0)
    is_online = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
