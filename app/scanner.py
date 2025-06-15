from flask import Blueprint, request, jsonify, redirect, url_for, flash, current_app
from markupsafe import escape
import os
import subprocess
import threading
import time
from datetime import datetime
import psutil

from .auth import login_required
from . import TASKS 
from .utils import parse_nmap_xml_python_nmap, parse_nmap_output_simple

scanner_bp = Blueprint('scanner', __name__)

# --- Tool Execution Logic ---

def run_tool(task_id, command, raw_output_file, app):
    """The target function for the scanning thread. Writes to a specific file."""
    with app.app_context():
        try:
            # Ensure the parent directory for the output file exists
            os.makedirs(os.path.dirname(raw_output_file), exist_ok=True)
            
            with open(raw_output_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")

            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, universal_newlines=False, encoding='utf-8', errors='replace'
            )
            TASKS[task_id]['process'] = process
            TASKS[task_id]['status'] = 'running'

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                for line_str in process.stdout:
                    TASKS[task_id]['recent_output'].append(line_str.strip())
                    if len(TASKS[task_id]['recent_output']) > 100:
                        TASKS[task_id]['recent_output'].pop(0)
                    f.write(line_str)
            
            return_code = process.wait()
            TASKS[task_id]['status'] = 'completed' if return_code == 0 else 'failed'

            if TASKS[task_id]['status'] == 'failed':
                xml_path = TASKS[task_id].get('xml_output_file')
                if xml_path and (not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0):
                    msg = f"[Warning: Nmap failed and XML output may be missing or incomplete.]"
                    TASKS[task_id]['recent_output'].append(msg)
                    current_app.logger.warning(f"Nmap task {task_id} failed: {msg}")

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Status: {TASKS[task_id]['status']}\n")

        except Exception as e:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['recent_output'].append(f"ERROR IN run_tool: {str(e)}")
            current_app.logger.error(f"Error in run_tool for task {task_id}: {e}", exc_info=True)


def _create_and_start_task(tool_id, target_or_query, options_str):
    """Helper to create task dictionary, command, and start the thread with new directory structure."""
    TOOLS = current_app.config.get('TOOLS', {})
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'
    if not target_or_query and tool_id in ['nmap', 'sqlmap', 'dirb', 'curl', 'searchsploit']:
        return None, f'{TOOLS[tool_id]["name"]} query/target is required'

    tool_config = TOOLS[tool_id]
    task_id_str = f"{tool_id}_{int(time.time())}"
    
    # --- NEW: Path generation based on config ---
    formats = [f.strip() for f in tool_config.get('output_formats', 'raw').split(',')]
    tool_output_dir = os.path.join(OUTPUT_DIR, tool_id)
    
    raw_output_file_path = None
    xml_output_file_path = None

    if len(formats) > 1:
        # Multiple formats, use subdirectories
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, 'raw', f'{task_id_str}.txt')
        if 'xml' in formats:
            xml_output_file_path = os.path.join(tool_output_dir, 'xml', f'{task_id_str}.xml')
    else:
        # Single format, save directly in the tool's directory
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, f'{task_id_str}.txt')
    
    if not raw_output_file_path:
        # Fallback if config is weird, though it shouldn't happen
        return None, "Tool has no 'raw' output format defined in config."

    # Build the options string
    final_options = options_str
    default_opts = tool_config.get('default_options', '')
    if default_opts and default_opts not in final_options:
        final_options = f"{default_opts} {final_options}"
    
    # Add XML output flag for Nmap, ensuring it has a path
    if tool_id == 'nmap' and xml_output_file_path:
        os.makedirs(os.path.dirname(xml_output_file_path), exist_ok=True)
        if '-oX' not in final_options and '-oA' not in final_options:
            final_options = f"-oX \"{xml_output_file_path}\" {final_options}"

    command_params = {'target': target_or_query, 'query': target_or_query, 'options': final_options}
    command = tool_config['command'].format(**command_params)

    # Store the precise file paths in the task dictionary
    TASKS[task_id_str] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None,
        'original_target': target_or_query if tool_id == 'nmap' else None,
        'raw_output_file': raw_output_file_path,
        'xml_output_file': xml_output_file_path
    }

    app = current_app._get_current_object()
    thread = threading.Thread(target=run_tool, args=(task_id_str, command, raw_output_file_path, app))
    thread.daemon = True
    thread.start()
    return task_id_str, None

# --- Scanner API and Action Routes ---

@scanner_bp.route('/home/scan', methods=['POST'])
@login_required
def home_scan():
    target = request.form.get('target')
    intensity = request.form.get('intensity', 'low')
    INTENSITY_TOOL_CONFIG = current_app.config.get('INTENSITY_TOOL_CONFIG', {})
    TOOLS = current_app.config.get('TOOLS', {})

    if not target:
        flash('Target is required.', 'danger')
        return redirect(url_for('main.home'))

    tool_config_map = INTENSITY_TOOL_CONFIG.get(intensity, {})
    if not tool_config_map:
        flash(f'No tools for intensity "{intensity}". Using default Nmap.', 'warning')
        tool_config_map = {'nmap': TOOLS.get('nmap', {}).get('default_options', '-v -sV')}

    task_ids = []
    for tool_id, options in tool_config_map.items():
        task_id, err = _create_and_start_task(tool_id, target, options)
        if err:
            flash(f"Error starting {tool_id}: {err}", 'danger')
        if task_id:
            task_ids.append(task_id)

    if not task_ids:
        flash('No tasks could be started.', 'danger')
        return redirect(url_for('main.home'))
        
    flash(f'Successfully started {len(task_ids)} scan(s).', 'success')
    return redirect(url_for('main.list_tasks'))


@scanner_bp.route('/task/<task_id>/status')
@login_required
def task_status(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    task_info = TASKS[task_id]
    
    # Simple sanitization for display
    cleaned_output = [escape(line) for line in task_info.get('recent_output', [])]
    return jsonify({'status': task_info['status'], 'recent_output': cleaned_output})


@scanner_bp.route('/task/<task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    if task_info['status'] == 'running' and task_info.get('process'):
        
        # --- MODIFICATION START: Use psutil for robust process termination ---
        try:
            # Get the parent process using its PID
            parent = psutil.Process(task_info['process'].pid)
            
            # Kill all child processes (e.g., nmap.exe spawned by cmd.exe)
            # The list() is important to avoid iteration issues while killing
            for child in parent.children(recursive=True):
                child.kill()
            
            # Kill the parent shell process itself
            parent.kill()
            
            task_info['status'] = 'stopped'
            TASKS[task_id]['recent_output'].append("[INFO] Task manually stopped by user.")
            
            # Optional: Write final status to file immediately
            output_file = task_info.get('raw_output_file')
            if output_file and os.path.exists(output_file):
                 with open(output_file, 'a', encoding='utf-8') as f:
                    f.write("\n--- Task manually stopped by user ---\n")
                    f.write(f"Status: {task_info['status']}\n")

            return jsonify({'status': 'success', 'message': 'Task and all related processes stopped.'})

        except psutil.NoSuchProcess:
            # The process may have finished just before the stop button was clicked
            task_info['status'] = 'stopped' # Update status to prevent inconsistencies
            return jsonify({'status': 'success', 'message': 'Process already finished.'})
        except Exception as e:
            current_app.logger.error(f"Error stopping task {task_id} with psutil: {e}")
            return jsonify({'status': 'error', 'message': f'Error stopping task: {str(e)}'}), 500
        # --- END MODIFICATION ---

    return jsonify({'status': 'error', 'message': 'Task is not running or process not found'}), 400
