# /S2E/app/scanner/services.py
# UPDATED: All task creation and updates now use the database.

from flask import current_app
import os
import subprocess
import threading
from datetime import datetime
import time
import shlex

# Import database and Task model
from app import db
from app.models import Task

def run_tool(task_id, command_list, command_str_for_log, raw_output_file, app):
    """The target function for the scanning thread. Updates the database record."""
    with app.app_context():
        task = None
        try:
            # Fetch the task from the database
            task = Task.query.get(task_id)
            if not task:
                current_app.logger.error(f"FATAL: Task {task_id} not found in database for thread.")
                return

            os.makedirs(os.path.dirname(raw_output_file), exist_ok=True)
            
            with open(raw_output_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {command_str_for_log}\n")
                f.write(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write("-" * 50 + "\n")

            process = subprocess.Popen(
                command_list, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, universal_newlines=False, encoding='utf-8', errors='replace'
            )
            
            # Update task with PID and running status
            task.pid = process.pid
            task.status = 'running'
            db.session.commit()

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                for line_str in process.stdout:
                    f.write(line_str)
            
            return_code = process.wait()
            
            # Final status update
            task.status = 'completed' if return_code == 0 else 'failed'
            task.pid = None # Clear PID as process is finished
            db.session.commit()

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Finished: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write(f"Status: {task.status}\n")

        except Exception as e:
            if task:
                task.status = 'error'
                task.pid = None
                db.session.commit()
            current_app.logger.error(f"Error in run_tool for task {task_id}: {e}", exc_info=True)


def _create_and_start_task(tool_id, target_or_query, options_str):
    """Helper to create a database Task record and start the thread."""
    TOOLS = current_app.config.get('TOOLS', {})
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    # ... (initial validation logic is the same) ...
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'
    if not target_or_query:
        return None, f'{TOOLS.get(tool_id, {}).get("name", "Tool")} query/target is required'

    tool_config = TOOLS[tool_id]
    
    # Generate timestamped filename base before creating the record
    filename_base = f"{tool_id}_{int(time.time())}"
    
    # ... (logic for building file paths is the same) ...
    # ...
    # ...

    # --- Create the Task record in the database ---
    new_task = Task(
        tool_id=tool_id,
        command="pending", # Will be updated below
        original_target=target_or_query if tool_id == 'nmap' else None,
        # Paths are now stored in the DB
        raw_output_file=raw_output_file_path,
        xml_output_file=xml_output_file_path
    )
    db.session.add(new_task)
    db.session.commit() # Commit to get a task ID

    # Now that we have an ID, we can finalize the command and paths
    task_id_str = str(new_task.id) # Use the database ID
    
    # ... (logic for building command_list_for_exec and command_for_display is the same as before) ...
    # ...
    # ...

    # Now update the task record with the final command string
    new_task.command = command_for_display
    db.session.commit()

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=run_tool,
        args=(new_task.id, command_list_for_exec, command_for_display, raw_output_file_path, app)
    )
    thread.daemon = True
    thread.start()
    
    return task_id_str, None