from flask_socketio import SocketIO

# Allow corridors for dev; restrict in prod
socketio = SocketIO(cors_allowed_origins="*")
