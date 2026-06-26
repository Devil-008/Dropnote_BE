import secrets
from .. import db
from ..models import Note

class NoteService:

    @staticmethod
    def create_note():
        """Creates a new note with a unique share token."""
        import random
        while True:
            share_token = f"{random.randint(100000, 999999)}"
            if not Note.query.filter_by(share_token=share_token).first():
                break
        
        new_note = Note(
            share_token=share_token,
            content={
                "html": ""
            }
        )
        db.session.add(new_note)
        db.session.commit()
        return new_note

    @staticmethod
    def get_note_by_token(token):
        """Retrieves a note by its share token."""
        return Note.query.filter_by(share_token=token).first()

    @staticmethod
    def update_note_content(token, content):
        """Updates the content of a note."""
        note = NoteService.get_note_by_token(token)
        if note:
            note.content = content
            db.session.commit()
            return note
        return None

    @staticmethod
    def delete_note(token):
        """Deletes a note by its share token."""
        note = NoteService.get_note_by_token(token)
        if note:
            db.session.delete(note)
            db.session.commit()
            return True
        return False
