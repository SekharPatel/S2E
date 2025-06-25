# /S2E/run.py

from app import create_app, TASKS
import os

app = create_app()

if __name__ == '__main__':
    # Ensure output directory exists before running
    output_dir = os.path.join(os.path.dirname(__file__), 'app', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if config was loaded successfully
    if not app.config.get('TOOLS'):
         print("ERROR: Configuration could not be loaded. Please check app/config and logs.")
         print("Application will exit.")
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)