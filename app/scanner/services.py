# /S2E/app/scanner/services.py
# UPDATED: All task creation and updates now use the database.

from flask import current_app
import os
import subprocess
import threading
from datetime import datetime
import time
import shlex

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


def _create_and_start_task(tool_id, target_or_query, options_str, project_id):
    """UPDATED: Helper to create a DB Task record and start the thread, linking it to a project."""
    TOOLS = current_app.config.get('TOOLS', {})
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'
    if not target_or_query:
        return None, f'{TOOLS.get(tool_id, {}).get("name", "Tool")} query/target is required'

    tool_config = TOOLS[tool_id]
    
    filename_base = f"{tool_id}_{int(time.time())}"
    
    formats = [f.strip() for f in tool_config.get('output_formats', 'raw').split(',')]
    tool_output_dir = os.path.join(OUTPUT_DIR, tool_id)
    raw_output_file_path = None
    xml_output_file_path = None
    if len(formats) > 1:
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, 'raw', f'{filename_base}.txt')
        if 'xml' in formats:
            xml_output_file_path = os.path.join(tool_output_dir, 'xml', f'{filename_base}.xml')
    else:
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, f'{filename_base}.txt')
    if not raw_output_file_path:
        return None, "Tool has no 'raw' output format defined in config."

    # --- Create the Task record in the database ---
    new_task = Task(
        tool_id=tool_id,
        command="pending",
        original_target=target_or_query if tool_id == 'nmap' else None,
        raw_output_file=raw_output_file_path,
        xml_output_file=xml_output_file_path,
        project_id=project_id  # <-- LINK THE TASK TO THE PROJECT
    )
    db.session.add(new_task)
    db.session.commit()

    task_id_str = str(new_task.id)

    # ... The rest of the command generation logic is unchanged ...
    options_list = shlex.split(options_str)
    final_options_list = options_list
    default_opts_str = tool_config.get('default_options', '')
    if default_opts_str:
        default_opts_list = shlex.split(default_opts_str)
        if not all(opt in final_options_list for opt in default_opts_list):
            final_options_list = default_opts_list + final_options_list
    if tool_id == 'nmap' and xml_output_file_path:
        os.makedirs(os.path.dirname(xml_output_file_path), exist_ok=True)
        if '-oX' not in final_options_list and '-oA' not in final_options_list:
            final_options_list = ['-oX', xml_output_file_path] + final_options_list
    base_command_list = shlex.split(tool_config['command'])
    command_list_for_exec = []
    for part in base_command_list:
        if part == '{target}' or part == '{query}':
            command_list_for_exec.append(target_or_query)
        elif part == '{options}':
            command_list_for_exec.extend(final_options_list)
        else:
            command_list_for_exec.append(part)
    command_for_display = ' '.join(command_list_for_exec)
    
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