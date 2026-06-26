from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
from celery import Celery
from .core.config import Config

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")

def make_celery(app_name):
    return Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND
    )

celery = make_celery(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app)
    db.init_app(app)
    socketio.init_app(app, message_queue=Config.REDIS_URL)

    # Register Blueprints
    from .api.files import files_bp
    from .api.notes import notes_bp
    from .api.health import health_bp
    
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    app.register_blueprint(health_bp, url_prefix='/api/health')

    # Ensure upload directory exists
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)

    # Register WebSockets
    from .websockets import events

    return app

import os
