# /S2E/app/main.py

from flask import Blueprint, render_template, redirect, url_for, session, current_app
from .auth import login_required
from . import TASKS # Import the shared TASKS dictionary
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('main.home'))
    return render_template('index.html')

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
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    tool_name = TOOLS.get(task_info['tool_id'], {}).get('name', 'Unknown Tool')
    output_content = ""
    output_file = os.path.join(OUTPUT_DIR, f"{task_id}.txt")
    
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                output_content = f.read()
            # Properly escape HTML entities while preserving formatting
            output_content = (output_content
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>')
                .replace(' ', '&nbsp;')
            )
        except Exception as e:
            output_content = f"Error reading output: {str(e)}"
    
    show_analysis_tab = task_info.get('tool_id') == 'nmap'

    return render_template(
        'task_details.html',
        task_id=task_id,
        task=task_info,
        tool_name=tool_name,
        output=output_content,
        show_analysis_tab=show_analysis_tab,
        follow_up_actions=FOLLOW_UP_ACTIONS
    )