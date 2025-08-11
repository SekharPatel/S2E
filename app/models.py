# /S2E/app/models.py
# UPDATED: Add Project and Target models and their relationships.

from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import relationship
import json
from flask_login import UserMixin


# Many-to-many relationship table between Project and Playbook
project_playbooks = db.Table('project_playbooks',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('playbook_id', db.Integer, db.ForeignKey('playbook.id'), primary_key=True)
)

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
    jobs = db.relationship('JobQueue', backref='project', lazy='dynamic', cascade="all, delete-orphan")
    
    # Many-to-many relationship with Playbook
    linked_playbooks = db.relationship('Playbook', secondary=project_playbooks, lazy='subquery',
                                       backref=db.backref('linked_projects', lazy=True))

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Add relationship to Project and Playbook
    projects = db.relationship('Project', backref='owner', lazy='dynamic')
    playbooks = db.relationship('Playbook', backref='owner', lazy='dynamic')

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

class JobQueue(db.Model):
    """
    Persistent job queue for background tasks.
    Replaces the in-memory deque for restart-safe task queuing.
    """
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(64), nullable=False)  # 'single_task' or 'playbook'
    job_data = db.Column(db.Text, nullable=False)  # JSON-encoded job data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(32), default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed'
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=0)  # Higher numbers = higher priority
    
    # Add Foreign Key to associate job with a project
    # Nullable=True for backward compatibility with old jobs without a project.
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    
    def set_job_data(self, data):
        """Store job data as JSON."""
        self.job_data = json.dumps(data)
    
    def get_job_data(self):
        """Retrieve job data from JSON."""
        try:
            return json.loads(self.job_data)
        except json.JSONDecodeError:
            return {}
    
    def __repr__(self):
        return f'<JobQueue {self.id} ({self.job_type})>'


class Playbook(db.Model):
    """
    A reusable playbook template that defines an automated testing workflow.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Trigger configuration - the initial scan that starts the playbook
    trigger_name = db.Column(db.String(128), nullable=False)
    trigger_tool_id = db.Column(db.String(64), nullable=False)
    trigger_options = db.Column(db.Text, nullable=False)
    
    # Foreign Key to associate playbook with the user who created it
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # NEW: Field to store the workflow data as JSON
    workflow_data = db.Column(db.Text, nullable=True)
    
    # Relationships
    rules = db.relationship('PlaybookRule', backref='playbook', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Playbook {self.name}>'

    def to_dict(self):
        """Convert playbook to dictionary format, including new workflow data."""
        return {
            'id': str(self.id),  # Keep as string for compatibility
            'name': self.name,
            'description': self.description or '',
            'trigger': {
                'name': self.trigger_name,
                'tool_id': self.trigger_tool_id,
                'options': self.trigger_options
            },
            'rules': [rule.to_dict() for rule in self.rules.all()],
            'workflow_data': self.workflow_data
        }


class PlaybookRule(db.Model):
    """
    Individual rules within a playbook that define actions based on discovered services.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # The services this rule applies to (stored as JSON list)
    on_service = db.Column(db.Text, nullable=False)  # JSON array like ["http", "https"]
    
    # Action configuration
    action_name = db.Column(db.String(128), nullable=False)
    action_tool_id = db.Column(db.String(64), nullable=False)
    action_options = db.Column(db.Text, nullable=False)
    
    # Foreign Key to associate rule with a playbook
    playbook_id = db.Column(db.Integer, db.ForeignKey('playbook.id'), nullable=False)

    def __repr__(self):
        return f'<PlaybookRule {self.id} ({self.action_name})>'

    def get_on_service_list(self):
        """Get the on_service field as a Python list."""
        try:
            return json.loads(self.on_service)
        except json.JSONDecodeError:
            return []

    def set_on_service_list(self, service_list):
        """Set the on_service field from a Python list."""
        self.on_service = json.dumps(service_list)

    def to_dict(self):
        """Convert rule to dictionary format similar to the old JSON structure."""
        return {
            'on_service': self.get_on_service_list(),
            'action': {
                'name': self.action_name,
                'tool_id': self.action_tool_id,
                'options': self.action_options
            }
        }