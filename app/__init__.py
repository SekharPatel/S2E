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

        # Create database tables for our models
        db.create_all()
        
        # Start the background task manager
        from .tasks.task_manager import start_task_manager
        start_task_manager(app)

    return app