# /S2E/app/scanner.py

from flask import Blueprint, request, jsonify, redirect, url_for, flash, current_app
import os
import subprocess
import threading
import time
from datetime import datetime

from .auth import login_required
from . import TASKS # Import the shared TASKS dictionary
from .utils import parse_nmap_xml_python_nmap, parse_nmap_output_simple # Import parsers from utils

scanner_bp = Blueprint('scanner', __name__)


# --- Tool Execution Logic ---

# MODIFICATION 1: Add 'app' as an argument and wrap the function in app.app_context()
def run_tool(task_id, command, output_dir, app):
    """The target function for the scanning thread."""
    # This 'with' block creates the necessary application context for the thread
    with app.app_context():
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{task_id}.txt")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")

            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, universal_newlines=False, encoding='utf-8', errors='replace'
            )
            TASKS[task_id]['process'] = process
            TASKS[task_id]['status'] = 'running'

            with open(output_file, 'a', encoding='utf-8') as f:
                for line_str in process.stdout:
                    TASKS[task_id]['recent_output'].append(line_str.strip())
                    if len(TASKS[task_id]['recent_output']) > 100:
                        TASKS[task_id]['recent_output'].pop(0)
                    f.write(line_str)
            
            return_code = process.wait()
            TASKS[task_id]['status'] = 'completed' if return_code == 0 else 'failed'

            if TASKS[task_id]['status'] == 'failed':
                if TASKS[task_id]['tool_id'] == 'nmap' and TASKS[task_id].get('xml_output_file'):
                    xml_path = TASKS[task_id]['xml_output_file']
                    if not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0:
                        msg = f"[Warning: Nmap failed and XML output '{xml_path}' may be missing or incomplete.]"
                        TASKS[task_id]['recent_output'].append(msg)
                        # Now this logger call will work correctly
                        current_app.logger.warning(f"Nmap task {task_id} failed: {msg}")

            with open(output_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Status: {TASKS[task_id]['status']}\n")

        except Exception as e:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['recent_output'].append(f"ERROR IN run_tool: {str(e)}")
            # This logger call will also work correctly now
            current_app.logger.error(f"Error in run_tool for task {task_id}: {e}")


def _create_and_start_task(tool_id, target_or_query, options_str):
    """Helper to create task dictionary, command, and start the thread."""
    TOOLS = current_app.config.get('TOOLS', {})
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'
    if not target_or_query and tool_id in ['nmap', 'sqlmap', 'dirb', 'curl', 'searchsploit']:
        return None, f'{TOOLS[tool_id]["name"]} query/target is required'

    tool_config = TOOLS[tool_id]
    task_id_str = f"{tool_id}_{int(time.time())}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    xml_output_file_path = None
    final_options_str = options_str

    if tool_id == 'nmap':
        # Use os.path.join for cross-platform compatibility
        xml_output_file_path = os.path.join(OUTPUT_DIR, f"{task_id_str}.xml")
        if '-oX' not in final_options_str and '-oA' not in final_options_str:
            final_options_str = f"-oX \"{xml_output_file_path}\" {final_options_str}"

    # Use a dictionary for .format() to avoid errors if one key is missing
    command_params = {'target': target_or_query, 'query': target_or_query, 'options': final_options_str}
    command = tool_config['command'].format(**command_params)

    TASKS[task_id_str] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None,
        'original_target': target_or_query if tool_id == 'nmap' else None,
        'xml_output_file': xml_output_file_path if tool_id == 'nmap' else None
    }

    # MODIFICATION 2: Get the real app object and pass it to the thread
    app = current_app._get_current_object()
    thread = threading.Thread(target=run_tool, args=(task_id_str, command, OUTPUT_DIR, app))
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
    cleaned_output = [line.replace('<', '<').replace('>', '>') for line in task_info.get('recent_output', [])]
    
    return jsonify({'status': task_info['status'], 'recent_output': cleaned_output})


@scanner_bp.route('/task/<task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    if task_info['status'] == 'running' and task_info.get('process'):
        try:
            task_info['process'].terminate()
            task_info['status'] = 'stopped'
            return jsonify({'status': 'success', 'message': 'Task stopped'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'Task is not running'}), 400


@scanner_bp.route('/task/<task_id>/analyze_nmap', methods=['GET'])
@login_required
def analyze_nmap_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    task_info = TASKS[task_id]
    if task_info['tool_id'] != 'nmap':
        return jsonify({'status': 'error', 'message': 'Analysis only for Nmap tasks'}), 400

    xml_file = task_info.get('xml_output_file')
    if xml_file and os.path.exists(xml_file) and os.path.getsize(xml_file) > 0:
        try:
            parsed_data = parse_nmap_xml_python_nmap(xml_file)
            if parsed_data.get("error"):
                 return jsonify({'status': 'error', 'message': parsed_data["error"], 'source': 'xml_error'}), 500
            return jsonify({'status': 'success', 'data': parsed_data, 'source': 'xml'})
        except Exception as e:
            current_app.logger.error(f"Error parsing Nmap XML for {task_id}: {e}")
            return jsonify({'status': 'error', 'message': f'XML parsing failed: {e}'}), 500
    
    # Fallback to text parsing
    output_file = os.path.join(current_app.config['OUTPUT_DIR'], f"{task_id}.txt")
    if not os.path.exists(output_file):
        return jsonify({'status': 'error', 'message': 'Nmap output files not found'}), 404
    
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
    parsed_data = parse_nmap_output_simple(content)
    parsed_data["warning"] = "Could not find or parse XML file. Results are from raw text and may be incomplete."
    return jsonify({'status': 'success', 'data': parsed_data, 'source': 'text'})


@scanner_bp.route('/task/run_follow_up', methods=['POST'])
@login_required
def run_follow_up_action():
    data = request.json
    action_id = data.get('action_id')
    service_info = data.get('service_info', {})
    original_nmap_target = data.get('original_nmap_target')

    FOLLOW_UP_ACTIONS = current_app.config.get('FOLLOW_UP_ACTIONS', {})
    TOOLS = current_app.config.get('TOOLS', {})

    if not all([action_id, service_info, original_nmap_target]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters.'}), 400
    if action_id not in FOLLOW_UP_ACTIONS:
        return jsonify({'status': 'error', 'message': 'Invalid follow-up action.'}), 400

    action_config = FOLLOW_UP_ACTIONS[action_id]
    tool_id = action_config['tool_id']
    options = action_config.get('default_options', '')
    
    try:
        query_params = {**service_info, 'target_host': original_nmap_target, 'specific_host_ip': service_info.get('host_ip', original_nmap_target)}
        target = action_config['query_format'].format(**query_params)
    except KeyError as e:
        return jsonify({'status': 'error', 'message': f'Missing key for query: {e}'}), 400

    task_id, err = _create_and_start_task(tool_id, target, options)

    if err:
        return jsonify({'status': 'error', 'message': err}), 500

    return jsonify({
        'status': 'success',
        'message': f'Started follow-up: {TOOLS[tool_id]["name"]} for "{target}"',
        'task_id': task_id
    })