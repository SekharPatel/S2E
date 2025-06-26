# /S2E/app/models.py
# NEW FILE: Defines the database models for the application.

from . import db  # Import the db object from the app package
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.String(64), nullable=False)
    command = db.Column(db.String(1024), nullable=False)
    start_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.String(64), default='starting')
    pid = db.Column(db.Integer, nullable=True) # Store the Process ID
    
    # Store the original target for context, especially for Nmap
    original_target = db.Column(db.String(256), nullable=True)
    
    # Store paths to output files
    raw_output_file = db.Column(db.String(512), nullable=True)
    xml_output_file = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f'<Task {self.id} ({self.tool_id})>'