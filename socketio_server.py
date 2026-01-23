from flask import Flask, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Simple in-memory mapping for demo ---
user_rooms = {}

@app.route('/')
def index():
    return 'SocketIO server running.'

@socketio.on('join')
def handle_join(data):
    user_id = data.get('user_id')
    room = data.get('room') or user_id
    join_room(room)
    user_rooms[user_id] = room
    emit('status', {'msg': f'{user_id} joined room {room}'}, room=room)

@socketio.on('leave')
def handle_leave(data):
    user_id = data.get('user_id')
    room = user_rooms.get(user_id)
    leave_room(room)
    emit('status', {'msg': f'{user_id} left room {room}'}, room=room)

@socketio.on('client_message')
def handle_client_message(data):
    user_id = data.get('user_id')
    admin_id = data.get('admin_id', 'admin')
    msg = data.get('message')
    room = user_rooms.get(user_id)
    emit('admin_message', {'user_id': user_id, 'message': msg}, room=admin_id)
    emit('client_message', {'user_id': user_id, 'message': msg}, room=room)

@socketio.on('admin_message')
def handle_admin_message(data):
    admin_id = data.get('admin_id', 'admin')
    user_id = data.get('user_id')
    msg = data.get('message')
    room = user_rooms.get(user_id)
    emit('client_message', {'admin_id': admin_id, 'message': msg}, room=room)
    emit('admin_message', {'admin_id': admin_id, 'message': msg}, room=admin_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
