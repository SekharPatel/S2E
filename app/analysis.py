from flask import Blueprint, request, jsonify, current_app
import os

from .auth import login_required
from . import TASKS
from .utils import parse_nmap_xml_python_nmap, parse_nmap_output_simple
from .scanner import _create_and_start_task

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/task/<task_id>/analyze_nmap', methods=['GET'])
@login_required
def analyze_nmap_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    task_info = TASKS[task_id]
    if task_info.get('tool_id') != 'nmap':
        return jsonify({'status': 'error', 'message': 'Analysis only for Nmap tasks'}), 400

    # Get file paths directly from the task dictionary
    xml_file = task_info.get('xml_output_file')
    raw_file = task_info.get('raw_output_file')

    if xml_file and os.path.exists(xml_file) and os.path.getsize(xml_file) > 0:
        try:
            parsed_data = parse_nmap_xml_python_nmap(xml_file)
            if parsed_data.get("error"):
                 return jsonify({'status': 'error', 'message': parsed_data["error"], 'source': 'xml_error'}), 500
            return jsonify({'status': 'success', 'data': parsed_data, 'source': 'xml'})
        except Exception as e:
            current_app.logger.error(f"Error parsing Nmap XML for {task_id}: {e}")
            return jsonify({'status': 'error', 'message': f'XML parsing failed: {e}'}), 500
    
    # Fallback to text parsing if XML is missing or failed
    if not raw_file or not os.path.exists(raw_file):
        return jsonify({'status': 'error', 'message': 'Nmap output files not found'}), 404
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        content = f.read()
    parsed_data = parse_nmap_output_simple(content)
    parsed_data["warning"] = "Could not find or parse XML file. Results are from raw text and may be incomplete."
    return jsonify({'status': 'success', 'data': parsed_data, 'source': 'text'})


@analysis_bp.route('/task/run_follow_up', methods=['POST'])
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