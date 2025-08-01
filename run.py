# /S2E/run.py

from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Check if config was loaded successfully
    if not app.config.get('TOOLS'):
         print("ERROR: Configuration could not be loaded. Please check config/ directory and logs.")
         print("Application will exit.")
    else:
        # Start task manager only when running the web server
        from app.tasks.task_manager import start_task_manager
        start_task_manager(app)
        
        app.run(debug=True, host='0.0.0.0', port=5000)