# /S2E/app/__init__.py
# UPDATED: Initialize the database and remove old config logic.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
import secrets
import click

# Create database and migration instances outside the factory
db = SQLAlchemy()
migrate = Migrate()

def load_config(app, dir_path):
    # This function is now only for non-user/non-task configurations
    if not os.path.isdir(dir_path):
        app.logger.error(f"CRITICAL: Configuration directory not found at {dir_path}")
        return

    loaded_files = 0
    for filename in os.listdir(dir_path):
        if filename.endswith('.json'):
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                app.config.update(config_data)
                app.logger.info(f"Loaded config from {filename}")
                loaded_files += 1
            except Exception as e:
                app.logger.error(f"CRITICAL: An error occurred while loading {filename}: {e}")

    if loaded_files == 0:
        app.logger.error("CRITICAL: No configuration files were loaded.")

    if 'TOOLS' not in app.config:
        app.config['TOOLS'] = {}
        app.logger.error("CRITICAL: TOOLS configuration is missing.")

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    base_dir = os.path.abspath(os.path.join(app.instance_path, os.pardir))

    # --- Configuration ---
    app.config.from_mapping(
        # IMPORTANT: In production, load this from an env var or a secrets file
        SECRET_KEY='a-persistent-secret-key-that-does-not-change', 
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(base_dir, 'app.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        BASE_DIR=base_dir,
        CONFIG_DIR=os.path.join(base_dir, 'config'),
        OUTPUT_DIR=os.path.join(base_dir, 'output'),
    )

    os.makedirs(app.config['OUTPUT_DIR'], exist_ok=True)
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    load_config(app, app.config['CONFIG_DIR'])

    with app.app_context():
        from . import models # Import models so migrations can see them

        # --- Register Blueprints ---
        from .home.routes import home_bp
        from .auth.routes import auth_bp
        from .scanner.routes import scanner_bp
        from .tasks.routes import tasks_bp
        from .projects.routes import projects_bp
        from .tasks.task_manager import start_task_manager
        start_task_manager(app)  # Start the task manager

        app.register_blueprint(home_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(scanner_bp)
        app.register_blueprint(tasks_bp)
        app.register_blueprint(projects_bp)

        # app.add_url_rule('/', endpoint='home.index')
        
    # --- Add CLI command for user management ---
    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("password")
    def create_user(username, password):
        """Creates a new user with the given password."""
        if models.User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return
        
        new_user = models.User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"User '{username}' created successfully.")

    return app