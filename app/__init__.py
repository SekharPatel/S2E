# /S2E/app/__init__.py
# UPDATED: Registers the new 'home_bp' and points the root URL to 'home.index'.

from flask import Flask
import os
import json
import secrets

# load_config function remains the same...
def load_config(app, dir_path):
    """Loads configuration from all JSON files in a directory."""
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
            except json.JSONDecodeError as e:
                app.logger.error(f"CRITICAL: Error decoding JSON from {filename}: {e}.")
            except Exception as e:
                app.logger.error(f"CRITICAL: An unexpected error occurred while loading {filename}: {e}")

    if loaded_files > 0:
        app.logger.info(f"Configuration loaded successfully from {loaded_files} file(s).")
    else:
        app.logger.error("CRITICAL: No configuration files were loaded.")

    # Provide fallbacks for critical missing keys after attempting to load all files
    if 'USERS' not in app.config:
        app.config['USERS'] = {'admin': 'defaultfallbackpassword'}
        app.logger.warning("USERS configuration not found, using fallback.")
    if 'TOOLS' not in app.config:
        app.config['TOOLS'] = {}
        app.logger.error("CRITICAL: TOOLS configuration is missing.")


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuration ---
    app.config.from_mapping(
        SECRET_KEY=secrets.token_hex(16),
        BASE_DIR=os.path.abspath(os.path.join(app.instance_path, os.pardir)),
        CONFIG_DIR=os.path.join(os.path.abspath(os.path.join(app.instance_path, os.pardir)), 'config'),
        OUTPUT_DIR=os.path.join(os.path.abspath(os.path.join(app.instance_path, os.pardir)), 'output'),
    )

    os.makedirs(app.config['OUTPUT_DIR'], exist_ok=True)
    
    load_config(app, app.config['CONFIG_DIR'])

    with app.app_context():
        # --- Register Blueprints from new feature modules ---
        from .home.routes import home_bp # NEW
        from .auth.routes import auth_bp
        from .scanner.routes import scanner_bp
        from .tasks.routes import tasks_bp

        app.register_blueprint(home_bp) # NEW
        app.register_blueprint(auth_bp)
        app.register_blueprint(scanner_bp)
        app.register_blueprint(tasks_bp)

        # Make the root URL (/) point to the main landing page in the new 'home' blueprint
        app.add_url_rule('/', endpoint='home.index') # UPDATED
        
    return app