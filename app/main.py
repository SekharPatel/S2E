# /S2E/app/main.py

from flask import Blueprint, render_template, jsonify, redirect, url_for, session, current_app
from .auth import login_required
from . import TASKS
import os
from markupsafe import escape # Use the recommended escape function

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    # if 'username' in session:
    #     return redirect(url_for('main.home'))
    return render_template('home.html')

@main_bp.route('/home')
@login_required
def home():
    return render_template('home.html')

@main_bp.route('/tasks')
@login_required
def list_tasks():
    task_list = []
    TOOLS = current_app.config.get('TOOLS', {})
    for task_id_iter, task_info in TASKS.items():
        serializable_task = {
            'task_id': task_id_iter,
            'tool_id': task_info['tool_id'],
            'tool_name': TOOLS.get(task_info['tool_id'], {}).get('name', 'Unknown Tool'),
            'command': task_info['command'],
            'start_time': task_info['start_time'],
            'status': task_info['status'],
        }
        task_list.append(serializable_task)
    task_list.sort(key=lambda x: x['start_time'], reverse=True)
    return render_template('tasks.html', tasks=task_list)

@main_bp.route('/task/<task_id>')
@login_required
def task_details(task_id):
    if task_id not in TASKS:
        return redirect(url_for('main.list_tasks'))
        
    task_info = TASKS[task_id]
    TOOLS = current_app.config.get('TOOLS', {})
    FOLLOW_UP_ACTIONS = current_app.config.get('FOLLOW_UP_ACTIONS', {})
    
    tool_name = TOOLS.get(task_info['tool_id'], {}).get('name', 'Unknown Tool')
    
    show_analysis_tab = task_info.get('tool_id') == 'nmap'

    return render_template(
        'task_details.html',
        task_id=task_id,
        task=task_info,
        tool_name=tool_name,
        show_analysis_tab=show_analysis_tab,
        follow_up_actions=FOLLOW_UP_ACTIONS
    )

@main_bp.route('/api/task/<task_id>/output')
@login_required
def get_task_output(task_id):
    """API endpoint to get the full, raw output of a completed or running task."""
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    output_file = task_info.get('raw_output_file')

    if not output_file or not os.path.exists(output_file):
        return jsonify({
            'status': 'success', 
            'output': 'Output file not found or not yet created.'
        })

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Escape the content on the server to ensure it's always HTML-safe
        escaped_content = escape(content)
        
        return jsonify({'status': 'success', 'output': escaped_content})
    except Exception as e:
        current_app.logger.error(f"Error reading output file for task {task_id}: {e}")
        return jsonify({'status': 'error', 'message': f'Could not read output file: {str(e)}'}), 500