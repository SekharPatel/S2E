# /S2E/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os, json
import click
from flask.cli import with_appcontext
from flask import current_app

# Initialize extensions but do not attach them to an app yet
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """Application factory function."""
    app = Flask(__name__, instance_relative_config=True) # Tells Flask the instance folder exists

    try:
        os.makedirs(app.instance_path, exist_ok=True)  # Ensure the instance folder exists
    except OSError as e:
        raise RuntimeError(f"Could not create instance folder: {e}")
        exit(1)

    # Configure the database to be in the instance folder
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_dev_secret_key')
    app.config['OUTPUT_DIR'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output'))
    app.config['CONFIG_DIR'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config'))

    # Helper function to load JSON config files
    def load_json_config(filename):
        config_path = os.path.join(app.config['CONFIG_DIR'], filename)
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    # Load tool and other configurations
    app.config.update(load_json_config('tools.json'))
    app.config.update(load_json_config('follow_up_actions.json'))

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Import parts of our application
        from . import models # Important: Import models so Flask-Migrate can see them

        # Import and register blueprints
        from .home.routes import home_bp
        from .auth.routes import auth_bp
        from .projects.routes import projects_bp
        from .tasks.routes import tasks_bp
        from .scanner.routes import scanner_bp

        app.register_blueprint(home_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(projects_bp)
        app.register_blueprint(tasks_bp)
        app.register_blueprint(scanner_bp)



    # --- NEW: Master Initialization CLI Command ---
    @app.cli.command("init-db")
    @click.option('--username', default='admin', help='Username for the initial admin user.')
    @click.option('--password', default='admin', help='Password for the initial admin user.')
    @with_appcontext
    def init_db_command(username, password):
        """
        Clears existing data and initializes the database with a default user and playbooks.
        """
        from .models import User # , Playbook, PlaybookRule
        
        # 1. Drop and recreate tables
        click.echo("Dropping all database tables...")
        db.drop_all()
        click.echo("Creating all database tables...")
        db.create_all()
        click.echo("Tables created successfully.")
        
        # 2. Create the initial user
        if User.query.filter_by(username=username).first():
            click.echo(f"User '{username}' already exists. Skipping user creation.")
        else:
            user = User()
            user.username = username
            user.set_password(password)
            db.session.add(user)
            click.echo(f"Created initial user '{username}'.")
        
        # # 3. Seed the default playbooks
        # playbook_config_path = os.path.join(current_app.config['CONFIG_DIR'], 'playbooks.json')
        # if not os.path.exists(playbook_config_path):
        #     click.echo("WARNING: playbooks.json not found. No default playbooks will be seeded.")
        # else:
        #     with open(playbook_config_path, 'r') as f:
        #         data = json.load(f)
            
        #     playbooks_in_json = data.get("PLAYBOOKS", [])
        #     click.echo(f"Seeding {len(playbooks_in_json)} playbook(s) from config file...")

        #     for pb_data in playbooks_in_json:
        #         new_playbook = Playbook(
        #             name=pb_data['name'],
        #             description=pb_data['description'],
        #             trigger=pb_data['trigger']
        #         )
        #         db.session.add(new_playbook)
        #         db.session.flush() # Flush to get ID for rules

        #         for rule_data in pb_data.get('rules', []):
        #             new_rule = PlaybookRule(
        #                 on_service=rule_data['on_service'],
        #                 action=rule_data['action'],
        #                 playbook_id=new_playbook.id
        #             )
        #             db.session.add(new_rule)
        #         click.echo(f"  - Seeded playbook '{pb_data['name']}'.")



        db.session.commit()
        #click.secho("\nDatabase initialization complete!", fg='green', bold=True)
        click.secho(f"You can now log in with:", fg='yellow')
        click.secho(f"  Username: {username}", fg='yellow')
        click.secho(f"  Password: {password}", fg='yellow')

    return app