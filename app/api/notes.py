from flask import Blueprint, jsonify
from ..services.note_service import NoteService

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/', methods=['POST'])
def create_note():
    """Creates a new collaborative note."""
    note = NoteService.create_note()
    return jsonify({"token": note.share_token}), 201

@notes_bp.route('/<token>', methods=['GET'])
def get_note(token):
    """Retrieves the content of a specific note."""
    note = NoteService.get_note_by_token(token)
    if not note:
        return jsonify({"error": "Note not found"}), 404
        
    return jsonify({
        "token": note.share_token,
        "content": note.content,
        "updated_at": note.updated_at.isoformat()
    }), 200

@notes_bp.route('/<token>', methods=['DELETE'])
def delete_note(token):
    """Deletes a specific note."""
    success = NoteService.delete_note(token)
    if not success:
        return jsonify({"error": "Note not found"}), 404
        
    return jsonify({"message": "Note deleted successfully"}), 200
