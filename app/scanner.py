from flask import Blueprint, request, jsonify, redirect, url_for, flash, current_app
from markupsafe import escape
import os
import psutil

from .auth import login_required
from . import TASKS 
from .utils import parse_nmap_xml_python_nmap, parse_nmap_output_simple, run_tool, _create_and_start_task

scanner_bp = Blueprint('scanner', __name__)

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
