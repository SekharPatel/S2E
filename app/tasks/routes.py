# /S2E/app/tasks/routes.py
# UPDATED: All routes now query the Task model from the database.

from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app
from markupsafe import escape
import os
import psutil

# Import DB and models, remove old storage
from app import db
from app.models import Task
from app.auth.routes import login_required

tasks_bp = Blueprint('tasks', __name__, template_folder='../templates')

PROBE_PROCESSES = {} # Ephemeral dict to store live process objects for stopping

# --- Web Page Routes ---

@tasks_bp.route('/tasks')
@login_required
def list_tasks():
    task_list = []
    TOOLS = current_app.config.get('TOOLS', {})
    
    # Query database for all tasks, newest first
    tasks_from_db = Task.query.order_by(Task.start_time.desc()).all()

    for task in tasks_from_db:
        serializable_task = {
            'task_id': task.id,
            'tool_id': task.tool_id,
            'tool_name': TOOLS.get(task.tool_id, {}).get('name', 'Unknown Tool'),
            'command': task.command,
            # --- THIS IS THE FIX ---
            # Pass the raw datetime object, not a string version of it.
            'start_time': task.start_time,
            'status': task.status,
        }
        task_list.append(serializable_task)

    return render_template('tasks.html', tasks=task_list)

@tasks_bp.route('/task/<int:task_id>')
@login_required
def task_details(task_id):
    # Fetch a single task by its primary key, or return 404
    task = Task.query.get_or_404(task_id)
    
    TOOLS = current_app.config.get('TOOLS', {})
    FOLLOW_UP_ACTIONS = current_app.config.get('FOLLOW_UP_ACTIONS', {})
    tool_name = TOOLS.get(task.tool_id, {}).get('name', 'Unknown Tool')
    show_analysis_tab = task.tool_id == 'nmap'

    return render_template(
        'task_details.html',
        task_id=task.id,
        task=task,
        tool_name=tool_name,
        show_analysis_tab=show_analysis_tab,
        follow_up_actions=FOLLOW_UP_ACTIONS
    )

# --- API Endpoints ---

@tasks_bp.route('/api/task/<int:task_id>/output')
@login_required
def get_task_output(task_id):
    task = Task.query.get_or_404(task_id)
    output_file = task.raw_output_file

    if not output_file or not os.path.exists(output_file):
        return jsonify({'status': 'success', 'output': 'Output file not found or not yet created.'})

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'status': 'success', 'output': escape(content)})
    except Exception as e:
        current_app.logger.error(f"Error reading output file for task {task_id}: {e}")
        return jsonify({'status': 'error', 'message': f'Could not read output file: {str(e)}'}), 500

@tasks_bp.route('/api/task/<int:task_id>/status')
@login_required
def task_status(task_id):
    task = Task.query.get_or_404(task_id)
    # NOTE: recent_output is removed as it's not persisted. 
    # The frontend will now just update the status badge.
    return jsonify({'status': task.status})


@tasks_bp.route('/api/task/<int:task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.status == 'running' and task.pid is not None:
        try:
            parent = psutil.Process(task.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            
            task.status = 'stopped'
            task.pid = None
            db.session.commit()
            
            # Append a stop message to the output file for context
            if task.raw_output_file and os.path.exists(task.raw_output_file):
                 with open(task.raw_output_file, 'a', encoding='utf-8') as f:
                    f.write("\n--- Task manually stopped by user ---\n")

            return jsonify({'status': 'success', 'message': 'Task and all related processes stopped.'})
        except psutil.NoSuchProcess:
            task.status = 'stopped' # The process died on its own
            task.pid = None
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Process already finished.'})
        except Exception as e:
            current_app.logger.error(f"Error stopping task {task_id} with psutil: {e}")
            return jsonify({'status': 'error', 'message': f'Error stopping task: {str(e)}'}), 500
        
    return jsonify({'status': 'error', 'message': 'Task is not running or PID not found'}), 400