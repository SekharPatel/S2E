# /S2E/app/models.py
# UPDATED: Add Project and Target models and their relationships.

from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import relationship

# A Project is the top-level container for an engagement
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to associate project with a user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    targets = db.relationship('Target', backref='project', lazy='dynamic', cascade="all, delete-orphan")
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.name}>'

# A Target defines the scope (e.g., an IP, domain, or network range)
class Target(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(512), nullable=False) # The actual target string
    
    # Foreign Key to associate target with a project
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def __repr__(self):
        return f'<Target {self.value}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Add relationship to Project
    projects = db.relationship('Project', backref='owner', lazy='dynamic')

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
    pid = db.Column(db.Integer, nullable=True)
    
    original_target = db.Column(db.String(256), nullable=True)
    
    raw_output_file = db.Column(db.String(512), nullable=True)
    xml_output_file = db.Column(db.String(512), nullable=True)

    # Add Foreign Key to associate task with a project
    # Nullable=True for backward compatibility with old tasks without a project.
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    def __repr__(self):
        return f'<Task {self.id} ({self.tool_id})>'