# /S2E/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import json
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configuration
    # Use SQLite by default (production might use a different DB)
    app.config['SECRET_KEY'] = '2e8e1e3c6b7a9f4d5c8a1b3e6f9c2d5e8b7a4c1f6e9d2b5a8c1e4f7b0a3d6c9f2e5'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Paths
    app.config['CONFIG_DIR'] = os.path.join(app.root_path, '..', 'config')
    app.config['OUTPUT_DIR'] = os.path.join(app.root_path, '..', 'output')
    
    # Load tool configurations
    with open(os.path.join(app.config['CONFIG_DIR'], 'tools.json'), 'r') as f:
        app.config['TOOLS'] = json.load(f)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.home.routes import home_bp
    from app.projects.routes import projects_bp
    from app.scanner.routes import scanner_bp
    from app.tasks.routes import tasks_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(home_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(tasks_bp)

    # Initialize login manager user loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize task manager
    from app.tasks.task_manager import start_task_manager
    start_task_manager(app)

    # CLI Commands
    @app.cli.command('seed-playbooks')
    def seed_playbooks():
        """Seed the database with default playbooks from playbooks.json"""
        from app.models import User, Playbook, PlaybookRule
        
        print("Seeding playbooks from playbooks.json...")
        
        # Load playbooks.json
        playbooks_path = os.path.join(app.config['CONFIG_DIR'], 'playbooks.json')
        try:
            with open(playbooks_path, 'r') as f:
                playbooks_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: playbooks.json not found at {playbooks_path}")
            return
        except json.JSONDecodeError as e:
            print(f"Error parsing playbooks.json: {e}")
            return
        
        # Get the first user to own these default playbooks
        # In a real scenario, you might want to create a system user
        user = User.query.first()
        if not user:
            print("No users found. Creating system user for default playbooks...")
            user = User(username='system')
            user.set_password('system_default_password_change_me')
            db.session.add(user)
            db.session.commit()
            print("Created system user to own default playbooks.")
        
        playbooks_created = 0
        rules_created = 0
        
        for playbook_data in playbooks_data.get('PLAYBOOKS', []):
            # Check if playbook already exists (by name to avoid duplicates)
            existing_playbook = Playbook.query.filter_by(name=playbook_data['name']).first()
            if existing_playbook:
                print(f"Playbook '{playbook_data['name']}' already exists, skipping...")
                continue
            
            # Create new playbook
            trigger = playbook_data['trigger']
            new_playbook = Playbook(
                name=playbook_data['name'],
                description=playbook_data.get('description', ''),
                trigger_name=trigger['name'],
                trigger_tool_id=trigger['tool_id'],
                trigger_options=trigger['options'],
                user_id=user.id
            )
            
            db.session.add(new_playbook)
            db.session.flush()  # Get the ID for foreign key
            
            # Create playbook rules
            for rule_data in playbook_data.get('rules', []):
                action = rule_data['action']
                new_rule = PlaybookRule(
                    action_name=action['name'],
                    action_tool_id=action['tool_id'],
                    action_options=action['options'],
                    playbook_id=new_playbook.id
                )
                new_rule.set_on_service_list(rule_data['on_service'])
                db.session.add(new_rule)
                rules_created += 1
            
            playbooks_created += 1
            print(f"Created playbook: {playbook_data['name']} with {len(playbook_data.get('rules', []))} rules")
        
        try:
            db.session.commit()
            print(f"Successfully created {playbooks_created} playbooks and {rules_created} rules!")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing to database: {e}")

    return app