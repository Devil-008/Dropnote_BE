from flask import Blueprint, request, jsonify, send_from_directory, current_app
from ..services.file_service import FileService
from ..models import DownloadLog
from .. import db
import os

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload/init', methods=['POST'])
def init_upload():
    data = request.json
    name = data.get('name')
    size = data.get('size')
    mime = data.get('mime')
    
    if not name or not size:
        return jsonify({"error": "Missing name or size"}), 400
        
    file_record = FileService.initialize_upload(name, size, mime)
    return jsonify({
        "file_id": file_record.id,
        "upload_url": f"/api/files/upload/chunk/{file_record.id}"
    }), 201

@files_bp.route('/upload/chunk/<file_id>', methods=['POST'])
def upload_chunk(file_id):
    chunk_index = request.args.get('index', type=int)
    chunk_data = request.data
    
    if chunk_index is None:
        return jsonify({"error": "Missing chunk index"}), 400
        
    success, message = FileService.save_chunk(file_id, chunk_index, chunk_data)
    if not success:
        return jsonify({"error": message}), 404
        
    return jsonify({"message": message}), 200

@files_bp.route('/upload/finalize/<file_id>', methods=['POST'])
def finalize_upload(file_id):
    data = request.json
    total_chunks = data.get('total_chunks')
    password = data.get('password')
    expires_in = data.get('expires_in', 10) # Default to 10 minutes
    max_downloads = data.get('max_downloads')
    
    if total_chunks is None:
        return jsonify({"error": "Missing total chunks"}), 400
        
    success, result = FileService.finalize_upload(file_id, total_chunks)
    if not success:
        return jsonify({"error": result}), 400
        
    share = FileService.create_share(file_id, expires_in, password, max_downloads)
    
    return jsonify({
        "share_token": share.share_token,
        "share_url": f"/s/{share.share_token}",
        "expires_at": share.expires_at.isoformat()
    }), 200

@files_bp.route('/info/<token>', methods=['GET'])
def get_share_info(token):
    share = FileService.get_share_by_token(token)
    if not share:
        return jsonify({"error": "Share not found"}), 404
        
    return jsonify({
        "name": share.file.original_name,
        "size": share.file.size_bytes,
        "expires_at": share.expires_at.isoformat(),
        "requires_password": share.password_hash is not None,
        "download_count": share.download_count
    }), 200

@files_bp.route('/download/<token>', methods=['POST'])
def download_file(token):
    data = request.json or {}
    password = data.get('password')
    
    share = FileService.get_share_by_token(token)
    if not share:
        return jsonify({"error": "Share not found"}), 404
        
    if not FileService.validate_password(share, password):
        return jsonify({"error": "Invalid password"}), 401
        
    # Log download
    log = DownloadLog(
        share_id=share.id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    share.download_count += 1
    db.session.add(log)
    db.session.commit()
    
    directory = os.path.join(current_app.config['UPLOAD_FOLDER'], share.file.storage_path)
    response = send_from_directory(
        directory, 
        "original_file", 
        as_attachment=True, 
        download_name=share.file.original_name
    )
    
    @response.call_on_close
    def schedule_deletion():
        try:
            from ..tasks.cleanup import delete_share_task
            # Queue task with a short delay to ensure file locks are released by the OS
            delete_share_task.apply_async((share.id,), countdown=5)
        except Exception as e:
            print(f"Warning: Could not schedule delete_share_task after download. Celery/Redis might be down. Error: {e}")
            
    return response

@files_bp.route('/qrcodes/<filename>', methods=['GET'])
def get_qrcode(filename):
    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes')
    return send_from_directory(qr_dir, filename)
