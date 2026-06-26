from flask import request
from flask_socketio import emit, join_room, leave_room
from .. import socketio
from ..services.note_service import NoteService
import random

# Mapping socket_id -> {room, user_id, color}
socket_sessions = {}
# Mapping room -> dictionary of {user_id: {user_id, color}}
room_users = {}

LIGHT_COLORS = [
    '#38bdf8', # Sky blue
    '#f472b6', # Pink
    '#fb7185', # Rose
    '#34d399', # Emerald
    '#fbbf24', # Amber
    '#a78bfa', # Lavender
    '#2dd4bf', # Teal
    '#f87171', # Coral
]

@socketio.on('join_note')
def on_join(data):
    """Handles a client joining a note's room and registers their presence."""
    note_token = data.get('token')
    user_id = data.get('user_id')
    color = data.get('color')
    if not note_token or not user_id:
        return

    sid = request.sid
    join_room(note_token)
    
    initials = data.get('initials') or '??'
    
    # Register connection session details
    socket_sessions[sid] = {
        'room': note_token,
        'user_id': user_id,
        'color': color,
        'initials': initials
    }
    
    if note_token not in room_users:
        room_users[note_token] = {}
        
    room_users[note_token][user_id] = {
        'user_id': user_id,
        'color': color or random.choice(LIGHT_COLORS),
        'initials': initials
    }
    
    print(f"Client {sid} ({user_id}) joined room: {note_token}")
    
    # Broadcast updated user list to everyone in the room
    emit('presence_update', {
        'users': list(room_users[note_token].values())
    }, room=note_token)


@socketio.on('note_update')
def on_note_update(data):
    """Handles an update to the note from a client."""
    note_token = data.get('token')
    content = data.get('content')
    
    if not note_token or content is None:
        return

    # Update content in DB
    NoteService.update_note_content(note_token, content)
    
    # Broadcast change to others in the same room (token)
    emit('note_broadcast', {'content': content}, room=note_token, include_self=False)


@socketio.on('leave_note')
def on_leave(data):
    """Handles a client leaving a note's room."""
    note_token = data.get('token')
    user_id = data.get('user_id')
    if not note_token or not user_id:
        return
        
    sid = request.sid
    leave_room(note_token)
    
    if sid in socket_sessions:
        socket_sessions.pop(sid, None)
        
    if note_token in room_users and user_id in room_users[note_token]:
        # Only delete if this user has no other active sessions in the room
        still_present = any(
            info['room'] == note_token and info['user_id'] == user_id
            for info in socket_sessions.values()
        )
        if not still_present:
            del room_users[note_token][user_id]
            if not room_users[note_token]:
                del room_users[note_token]
                
    users = list(room_users[note_token].values()) if note_token in room_users else []
    emit('presence_update', {
        'users': users
    }, room=note_token)
    
    print(f"Client {sid} ({user_id}) left room: {note_token}")


@socketio.on('disconnect')
def on_disconnect():
    """Handles client disconnects automatically."""
    sid = request.sid
    if sid in socket_sessions:
        session_info = socket_sessions.pop(sid)
        room = session_info['room']
        user_id = session_info['user_id']
        
        # Check if the user is still connected on another session/tab
        still_present = any(
            info['room'] == room and info['user_id'] == user_id
            for info in socket_sessions.values()
        )
        
        if not still_present and room in room_users and user_id in room_users[room]:
            del room_users[room][user_id]
            if not room_users[room]:
                del room_users[room]
                
        # Broadcast presence update to remaining users in the room
        if room in room_users:
            emit('presence_update', {
                'users': list(room_users[room].values())
            }, room=room)
        else:
            # Broadcast empty user list if no one is left
            emit('presence_update', {
                'users': []
            }, room=room)
            
        print(f"Client {sid} ({user_id}) disconnected from room {room}")

@socketio.on('delete_note_broadcast')
def on_delete_broadcast(data):
    """Notifies everyone that the note has been deleted."""
    note_token = data.get('token')
    if not note_token:
        return
    emit('note_deleted_broadcast', {}, room=note_token, include_self=False)
