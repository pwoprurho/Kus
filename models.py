from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Existing Admin User Class
class User(UserMixin):
    def __init__(self, id, full_name, email, role, location=None):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.role = role
        self.location = location

    def get_id(self):
        return str(self.id)

    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)

# --- NEW CLIENT USER CLASS ---
class ClientUser(UserMixin):
    def __init__(self, id, email, full_name, recovery_key):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.recovery_key = recovery_key
        self.role = 'client' # Explicit role

    def get_id(self):
        return str(self.id)