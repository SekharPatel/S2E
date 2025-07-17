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
        app.config['TOOLS'] = json.load(f)["TOOLS"]

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.home.routes import home_bp
    from app.projects.routes import projects_bp
    from app.scanner.routes import scanner_bp
    from app.tasks.routes import tasks_bp
    from app.playbooks.routes import playbooks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(playbooks_bp)

    # Initialize login manager user loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    import click
    @app.cli.command('init-db')
    @click.option('--username', '-u', prompt=False, help='Username for the initial admin user')
    @click.option('--password', '-p', prompt=False, hide_input=True, help='Password for the initial admin user')
    @click.option('--force', '-f', is_flag=True, help='Force recreation of database even if it exists')
    @click.option('--skip-playbooks', is_flag=True, help='Skip seeding playbooks (only create user)')
    def init_db(username, password, force, skip_playbooks):
        """Initialize the database, create an initial user, and seed playbooks."""
        import getpass
        from app.models import User, Playbook, PlaybookRule
        import os

        def c_echo(msg, fg="green", bold=False):
            click.secho(msg, fg=fg, bold=bold)

        def check_database_exists():
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if db_path.startswith('/'):
                db_path = db_path[1:]
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
            return os.path.exists(db_path)

        def drop_database():
            c_echo('Dropping existing database tables...', fg="yellow")
            with app.app_context():
                db.drop_all()
                c_echo('✓ All tables dropped successfully', fg="green")

        def create_database():
            c_echo('Creating database tables...', fg="yellow")
            with app.app_context():
                db.create_all()
                c_echo('✓ Database tables created successfully', fg="green")

        def create_initial_user(username, password):
            c_echo(f"Creating initial user '{username}'...", fg="yellow")
            with app.app_context():
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    c_echo(f"✓ User '{username}' already exists", fg="cyan")
                    return existing_user
                user = User()
                user.username = username
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                c_echo(f"✓ User '{username}' created successfully", fg="green")
                return user

        def seed_playbooks(user_id):
            c_echo('Seeding playbooks from playbooks.json...', fg="yellow")
            playbooks_path = os.path.join(app.config['CONFIG_DIR'], 'playbooks.json')
            try:
                with open(playbooks_path, 'r') as f:
                    playbooks_data = json.load(f)
            except FileNotFoundError:
                c_echo(f"Error: playbooks.json not found at {playbooks_path}", fg="red", bold=True)
                return
            except json.JSONDecodeError as e:
                c_echo(f"Error parsing playbooks.json: {e}", fg="red", bold=True)
                return
            with app.app_context():
                user = User.query.get(user_id)
                playbooks_created = 0
                rules_created = 0
                for playbook_data in playbooks_data.get('PLAYBOOKS', []):
                    existing_playbook = Playbook.query.filter_by(name=playbook_data['name']).first()
                    if existing_playbook:
                        c_echo(f"  - Playbook '{playbook_data['name']}' already exists, skipping...", fg="cyan")
                        continue
                    trigger = playbook_data['trigger']
                    new_playbook = Playbook()
                    new_playbook.name = playbook_data['name']
                    new_playbook.description = playbook_data.get('description', '')
                    new_playbook.trigger_name = trigger['name']
                    new_playbook.trigger_tool_id = trigger.get('tool_id')
                    new_playbook.trigger_options = trigger.get('options', {})
                    new_playbook.user_id = user.id if user else None
                    db.session.add(new_playbook)
                    db.session.flush()
                    for rule_data in playbook_data.get('rules', []):
                        action = rule_data['action']
                        new_rule = PlaybookRule()
                        new_rule.action_name = action['name']
                        new_rule.action_tool_id = action['tool_id']
                        new_rule.action_options = action['options']
                        new_rule.playbook_id = new_playbook.id
                        new_rule.set_on_service_list(rule_data['on_service'])
                        db.session.add(new_rule)
                        rules_created += 1
                    playbooks_created += 1
                    c_echo(f"  ✓ Created playbook: {playbook_data['name']} with {len(playbook_data.get('rules', []))} rules", fg="green")
                try:
                    db.session.commit()
                    c_echo(f"✓ Successfully created {playbooks_created} playbooks and {rules_created} rules!", fg="green", bold=True)
                except Exception as e:
                    db.session.rollback()
                    c_echo(f"Error committing playbooks to database: {e}", fg="red", bold=True)
                    raise click.ClickException(str(e))

        # --- Main logic ---
        # Prompt for credentials if not provided
        if not username:
            username = click.prompt(click.style('Enter username for initial admin user', fg="yellow"), type=str)
        if not password:
            password = getpass.getpass(click.style('Enter password for initial admin user: ', fg="yellow"))
            if not password:
                c_echo('Error: Password cannot be empty', fg="red", bold=True)
                raise click.ClickException('Password cannot be empty')
            password_confirm = getpass.getpass(click.style('Confirm password: ', fg="yellow"))
            if password != password_confirm:
                c_echo('Error: Passwords do not match', fg="red", bold=True)
                raise click.ClickException('Passwords do not match')

        db_exists = check_database_exists()
        if db_exists:
            if force:
                c_echo('Database exists. Force flag provided, recreating...', fg="yellow", bold=True)
                drop_database()
            else:
                c_echo('Database already exists!', fg="red", bold=True)
                if click.confirm(click.style('Do you want to recreate it? This will delete all existing data.', fg="yellow"), default=False):
                    drop_database()
                else:
                    c_echo('Database initialization cancelled.', fg="red", bold=True)
                    return
        create_database()
        user = create_initial_user(username, password)
        if not skip_playbooks:
            seed_playbooks(user.id)
        else:
            c_echo('Skipping playbook seeding as requested.', fg="yellow")
        c_echo('\n=== Database Initialization Complete ===', fg="green", bold=True)
        c_echo('✓ Database initialized successfully', fg="green")
        c_echo(f'✓ Admin user created: {username}', fg="green")
        if not skip_playbooks:
            c_echo('✓ Default playbooks seeded', fg="green")
        c_echo('\nYou can now start the application with: flask run', fg="cyan")
        # Print initial user and password at the end
        c_echo(f"\n{chr(0x2714)} Initial admin credentials:", fg="magenta", bold=True)
        c_echo(f"    Username: {username}", fg="magenta")
        c_echo(f"    Password: {password}", fg="magenta")

    return app