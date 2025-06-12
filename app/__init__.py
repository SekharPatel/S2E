# /S2E/app/__init__.py

from flask import Flask
import os
import json
import secrets

# --- In-memory Task Storage ---
# This dictionary will be shared across the application modules.
TASKS = {}

def load_config(app, file_path):
    """Loads configuration from a JSON file and attaches it to the app."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Attach config values to the app's config object
        app.config.update(config_data)
        
        # Provide fallbacks for critical missing keys
        if 'USERS' not in app.config:
            app.config['USERS'] = {'admin': 'defaultfallbackpassword'}
            app.logger.warning("USERS configuration not found, using fallback.")
        if 'TOOLS' not in app.config:
            app.config['TOOLS'] = {}
            app.logger.error("CRITICAL: TOOLS configuration is missing.")

        app.logger.info(f"Configuration loaded successfully from {file_path}")
        
    except FileNotFoundError:
        app.logger.error(f"CRITICAL: Configuration file {file_path} not found.")
    except json.JSONDecodeError as e:
        app.logger.error(f"CRITICAL: Error decoding JSON from {file_path}: {e}.")
    except Exception as e:
        app.logger.error(f"CRITICAL: An unexpected error occurred while loading config: {e}")


def create_app():
    """Create and configure an instance of the Flask application."""
    
    # When using a package, Flask automatically looks for 'static' and 'templates' folders
    # within the package directory, so we don't need to specify paths.
    app = Flask(__name__)

    # --- Load Configuration ---
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    
    # Define paths relative to the application's root directory
    app.config['BASE_DIR'] = os.path.abspath(os.path.dirname(__file__))
    app.config['CONFIG_FILE'] = os.path.join(app.config['BASE_DIR'], 'config.json')
    app.config['OUTPUT_DIR'] = os.path.join(app.config['BASE_DIR'], 'output')

    load_config(app, app.config['CONFIG_FILE'])

    with app.app_context():
        # --- Register Blueprints ---
        # Blueprints are imported here to avoid circular dependencies.
        from . import auth
        from . import main
        from . import scanner

        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(main.main_bp)
        app.register_blueprint(scanner.scanner_bp)

        # Make all routes available from the root, e.g., /login instead of /auth/login
        app.add_url_rule('/', endpoint='index')
        
    return app