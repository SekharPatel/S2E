import sys
from app import create_app, db
import os

app = create_app()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        with app.app_context():
            db.create_all()
        print("Database initialized.")
    elif len(sys.argv) > 1 and sys.argv[1] == 'test-config':
        if not app.config.get('TOOLS'):
            print("ERROR: Configuration could not be loaded. Please check config/ directory and logs.")
            print("Application will exit.")
        else:
            print("Configuration is OK.")
            print("Application will exit.")
    else:
        # Start task manager only when running the web server
        from app.routes.tasks.task_manager import start_task_manager
        start_task_manager(app)
        
        app.run(debug=True, host='0.0.0.0', port=5000)