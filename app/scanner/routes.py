# /S2E/app/scanner/routes.py
# UPDATED: This version removes the dependency on the old storage.py and uses the database.

from flask import Blueprint, redirect, url_for, current_app, request, flash, jsonify, session
import os

from app.auth.routes import login_required
from app.models import Task
from .services import _create_and_start_task
from .parsers import parse_nmap_xml_python_nmap, parse_nmap_output_simple

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/home/scan', methods=['POST'])
@login_required
def home_scan():
    # Get form data from the new 'Quick Run' tool launcher
    tool_id = request.form.get('tool_id')
    target = request.form.get('target')
    options = request.form.get('options', '')
    
    # Get the active project from the session
    active_project_id = session.get('active_project_id')

    if not tool_id or not target:
        flash('Tool and Target are required.', 'danger')
        return redirect(url_for('home.home'))

    if not active_project_id:
        flash('No active project. Please create or select a project first.', 'danger')
        return redirect(url_for('home.home'))

    # Call the service to create and start the task, now with a project_id
    task_id, err = _create_and_start_task(tool_id, target, options, project_id=active_project_id)

    if err:
        flash(f"Error starting {tool_id}: {err}", 'danger')
    else:
        flash(f'Successfully started task #{task_id} for tool {tool_id}.', 'success')
    
    # Redirect to the main tasks list to see it running
    return redirect(url_for('tasks.list_tasks'))

# --- API Endpoints ---
# (The API endpoints analyze_nmap_task and run_follow_up_action remain here unchanged)

@scanner_bp.route('/api/task/<int:task_id>/analyze_nmap', methods=['GET'])
@login_required
def analyze_nmap(task_id):
    # Fetch the task from the database or return a 404 error
    task_info = Task.query.get_or_404(task_id)

    if task_info.tool_id != 'nmap':
        return jsonify({'status': 'error', 'message': 'Analysis only for Nmap tasks'}), 400

    xml_file = task_info.xml_output_file
    raw_file = task_info.raw_output_file

    if xml_file and os.path.exists(xml_file) and os.path.getsize(xml_file) > 0:
        try:
            parsed_data = parse_nmap_xml_python_nmap(xml_file)
            if parsed_data.get("error"):
                 return jsonify({'status': 'error', 'message': parsed_data["error"], 'source': 'xml_error'}), 500
            return jsonify({'status': 'success', 'data': parsed_data, 'source': 'xml'})
        except Exception as e:
            current_app.logger.error(f"Error parsing Nmap XML for {task_id}: {e}")
            return jsonify({'status': 'error', 'message': f'XML parsing failed: {e}'}), 500
    
    if not raw_file or not os.path.exists(raw_file):
        return jsonify({'status': 'error', 'message': 'Nmap output files not found'}), 404
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        content = f.read()
    parsed_data = parse_nmap_output_simple(content)
    parsed_data["warning"] = "Could not find or parse XML file. Results are from raw text and may be incomplete."
    return jsonify({'status': 'success', 'data': parsed_data, 'source': 'text'})

@scanner_bp.route('/api/task/run_follow_up', methods=['POST'])
@login_required
def run_follow_up():
    data = request.json
    action_id = data.get('action_id')
    service_info = data.get('service_info', {})
    original_nmap_target = data.get('original_nmap_target')
    original_nmap_task_id = data.get('original_nmap_task_id') # <-- NEW: Get parent task ID

    FOLLOW_UP_ACTIONS = current_app.config.get('FOLLOW_UP_ACTIONS', {})
    TOOLS = current_app.config.get('TOOLS', {})

    # --- MODIFIED: Validation and Project ID retrieval ---
    if not all([action_id, service_info, original_nmap_target, original_nmap_task_id]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters.'}), 400
    if action_id not in FOLLOW_UP_ACTIONS:
        return jsonify({'status': 'error', 'message': 'Invalid follow-up action.'}), 400

    # Find the original task to get its project_id
    original_task = Task.query.get(original_nmap_task_id)
    if not original_task:
        return jsonify({'status': 'error', 'message': 'Original Nmap task not found.'}), 404
    
    project_id_for_followup = original_task.project_id
    if not project_id_for_followup:
        return jsonify({'status': 'error', 'message': 'Cannot run follow-up on a task that is not part of a project.'}), 400
    # --- END MODIFICATION ---

    action_config = FOLLOW_UP_ACTIONS[action_id]
    tool_id = action_config['tool_id']
    options = action_config.get('default_options', '')
    
    try:
        query_params = {**service_info, 'target_host': original_nmap_target, 'specific_host_ip': service_info.get('host_ip', original_nmap_target)}
        target = action_config['query_format'].format(**query_params)
    except KeyError as e:
        return jsonify({'status': 'error', 'message': f'Missing key for query: {e}'}), 400

    task_id, err = _create_and_start_task(tool_id, target, options, project_id=project_id_for_followup)

    if err:
        return jsonify({'status': 'error', 'message': err}), 500

    return jsonify({
        'status': 'success',
        'message': f'Started follow-up: {TOOLS[tool_id]["name"]} for "{target}"',
        'task_id': task_id
    })