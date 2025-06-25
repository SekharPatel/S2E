# /S2E/app/tasks/routes.py
# Key Changes: New blueprint. Combines task list/details pages and task status/stop APIs.

from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app
from markupsafe import escape
import os
import psutil

# Import from new locations
from app.auth.routes import login_required
from .storage import TASKS

tasks_bp = Blueprint('tasks', __name__, template_folder='../templates')

# --- Web Page Routes ---

@tasks_bp.route('/tasks')
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

@tasks_bp.route('/task/<task_id>')
@login_required
def task_details(task_id):
    if task_id not in TASKS:
        return redirect(url_for('tasks.list_tasks'))
        
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

# --- API Endpoints ---

@tasks_bp.route('/api/task/<task_id>/output')
@login_required
def get_task_output(task_id):
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
        
        escaped_content = escape(content)
        
        return jsonify({'status': 'success', 'output': escaped_content})
    except Exception as e:
        current_app.logger.error(f"Error reading output file for task {task_id}: {e}")
        return jsonify({'status': 'error', 'message': f'Could not read output file: {str(e)}'}), 500

@tasks_bp.route('/api/task/<task_id>/status')
@login_required
def task_status(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    task_info = TASKS[task_id]
    
    cleaned_output = [escape(line) for line in task_info.get('recent_output', [])]
    return jsonify({'status': task_info['status'], 'recent_output': cleaned_output})


@tasks_bp.route('/api/task/<task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    if task_info['status'] == 'running' and task_info.get('process'):
        try:
            parent = psutil.Process(task_info['process'].pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            
            task_info['status'] = 'stopped'
            TASKS[task_id]['recent_output'].append("[INFO] Task manually stopped by user.")
            
            output_file = task_info.get('raw_output_file')
            if output_file and os.path.exists(output_file):
                 with open(output_file, 'a', encoding='utf-8') as f:
                    f.write("\n--- Task manually stopped by user ---\n")

            return jsonify({'status': 'success', 'message': 'Task and all related processes stopped.'})
        except psutil.NoSuchProcess:
            task_info['status'] = 'stopped'
            return jsonify({'status': 'success', 'message': 'Process already finished.'})
        except Exception as e:
            current_app.logger.error(f"Error stopping task {task_id} with psutil: {e}")
            return jsonify({'status': 'error', 'message': f'Error stopping task: {str(e)}'}), 500
        
    return jsonify({'status': 'error', 'message': 'Task is not running or process not found'}), 400