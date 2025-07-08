# /S2E/app/scanner/services.py
# REFACTORED: Now interacts with our custom task queue instead of threading.

from flask import current_app
import os
import shlex
import time

from app import db
from app.models import Task
from app.tasks.task_manager import TASK_QUEUE, QUEUE_LOCK

def _create_task_record(tool_id, target_or_query, options_str, project_id):
    """
    UPDATED: Ensures file paths in commands are properly quoted.
    """
    TOOLS = current_app.config.get('TOOLS', {})
    if not tool_id or tool_id not in TOOLS:
        return None, f"Invalid tool: {tool_id}"

    tool_config = TOOLS[tool_id]
    
    timestamp = int(time.time())
    filename_base = f"{tool_id}_{project_id}_{timestamp}"
    output_dir = current_app.config['OUTPUT_DIR']
    raw_output_file = os.path.join(output_dir, f'{filename_base}.txt')
    xml_output_file = os.path.join(output_dir, f'{filename_base}.xml')

    command_list_for_exec = []

    base_command_parts = shlex.split(tool_config['command'])
    
    options_list = shlex.split(options_str)
    
    if tool_id == 'nmap':
        if '-oX' not in options_list and '-oA' not in options_list:
            # Add the QUOTED path to the options list
            options_list.extend(['-oX', xml_output_file])

    for part in base_command_parts:
        if part == '{target}' or part == '{query}':
            command_list_for_exec.append(target_or_query)
        elif part == '{options}':
            command_list_for_exec.extend(options_list)
        else:
            command_list_for_exec.append(part)
            
    # Use shlex.join to create a command string that is safe to parse later
    command_for_display = shlex.join(command_list_for_exec)

    new_task = Task(
        tool_id=tool_id,
        command=command_for_display,
        project_id=project_id,
        raw_output_file=raw_output_file,
        # Save the clean path for the parser
        xml_output_file=xml_output_file if tool_id == 'nmap' else None,
        original_target=target_or_query if tool_id == 'nmap' else None
    )
    db.session.add(new_task)
    db.session.commit()
    
    return new_task.id, None    

def add_single_task_to_queue(tool_id, target, options, project_id):
    """
    Creates a single task record and adds it to the run queue.
    """
    task_id, err = _create_task_record(tool_id, target, options, project_id)
    if err:
        return None, err
        
    with QUEUE_LOCK:
        TASK_QUEUE.append({'type': 'single_task', 'task_id': task_id})
        
    return task_id, None

def add_project_scan_to_queue(tool_id, options, project_id):
    """
    Creates a task for every target in the project and adds them to the queue.
    """
    from app.models import Project
    project = Project.query.get(project_id)
    if not project:
        return 0, "Project not found"
        
    targets = project.targets.all()
    if not targets:
        return 0, "Project has no targets"

    tasks_added = 0
    for target in targets:
        task_id, err = add_single_task_to_queue(tool_id, target.value, options, project_id)
        if not err:
            tasks_added += 1
            
    return tasks_added, None