# /S2E/app/__init__.py

from flask import Flask
import os
import json
import secrets

# --- In-memory Task Storage ---
# This dictionary will be shared across the application modules.
TASKS = {}

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
    
    # When using a package, Flask automatically looks for 'static' and 'templates' folders
    # within the package directory, so we don't need to specify paths.
    app = Flask(__name__)

    # --- Load Configuration ---
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    
    # Define paths relative to the application's root directory
    app.config['BASE_DIR'] = os.path.abspath(os.path.dirname(__file__))
    app.config['CONFIG_DIR'] = os.path.join(app.config['BASE_DIR'], 'config')
    app.config['OUTPUT_DIR'] = os.path.join(app.config['BASE_DIR'], 'output')

    load_config(app, app.config['CONFIG_DIR'])

    with app.app_context():
        # --- Register Blueprints ---
        # Blueprints are imported here to avoid circular dependencies.
        from . import auth
        from . import main
        from . import scanner
        from . import analysis

        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(main.main_bp)
        app.register_blueprint(scanner.scanner_bp)
        app.register_blueprint(analysis.analysis_bp)

        # Make all routes available from the root, e.g., /login instead of /auth/login
        app.add_url_rule('/', endpoint='index')
        
    return app