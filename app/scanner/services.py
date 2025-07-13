# /S2E/app/scanner/services.py

from flask import current_app
import os
import shlex
import time

from app import db
from app.models import Task
from app.tasks.task_manager import add_job_to_queue
from app.utils.validation import (
    validate_tool_id, sanitize_command_options, validate_target, 
    validate_file_path, ValidationError, normalize_path
)

def _create_task_record(tool_id, target_or_query, options_str, project_id):
    """
    UPDATED: Ensures file paths in commands are properly quoted and validated.
    """
    # Validate tool_id
    if not validate_tool_id(tool_id):
        return None, f"Invalid tool: {tool_id}"

    # Validate target/query
    if not validate_target(target_or_query):
        return None, f"Invalid target/query: {target_or_query}"

    # Sanitize options
    options_str = sanitize_command_options(options_str)

    TOOLS = current_app.config.get('TOOLS', {})
    tool_config = TOOLS[tool_id]
    
    if not tool_config:
        return None, f"Tool configuration not found: {tool_id}"
    
    if 'command' not in tool_config:
        return None, f"Tool configuration missing command field: {tool_id}"
    
    # Build the command first
    command_list_for_exec = []

    base_command_parts = shlex.split(tool_config['command'])
    
    options_list = shlex.split(options_str)
    
    # We'll add the XML output path after we have the filename
    if tool_id == 'nmap':
        if '-oX' not in options_list and '-oA' not in options_list:
            # We'll add the XML output path later after we have the filename
            pass

    for part in base_command_parts:
        if part == '{target}' or part == '{query}':
            command_list_for_exec.append(target_or_query)
        elif part == '{options}':
            command_list_for_exec.extend(options_list)
        else:
            command_list_for_exec.append(part)
            
    # Create a readable command string for display (with proper quoting)
    def quote_part(part):
        """Quote a command part if it contains spaces or special characters."""
        if not part:
            return '""'
        
        # Check if part contains spaces, quotes, or other special characters
        needs_quotes = (
            ' ' in part or 
            "'" in part or 
            '"' in part or 
            # Don't quote just because of backslashes (common in Windows paths)
            any(char in part for char in ['&', '|', ';', '`', '$', '<', '>', '(', ')', '{', '}', '[', ']'])
        )
        
        if needs_quotes:
            # Use double quotes and escape any existing double quotes
            # For Windows paths, we need to be careful with backslashes
            if '\\' in part and '"' not in part:
                # Windows path without quotes - use double quotes
                return f'"{part}"'
            elif '"' in part:
                # Contains double quotes - escape them
                return f'"{part.replace('"', '\\"')}"'
            else:
                # Use single quotes for other cases
                return f"'{part}'"
        return part
    
    # Generate a temporary unique ID for filename generation
    temp_timestamp = int(time.time() * 1000)  # Use milliseconds for uniqueness
    
    # Generate filenames using temporary timestamp
    filename_base = f"{tool_id}_{project_id}_{temp_timestamp}"
    output_dir = normalize_path(current_app.config['OUTPUT_DIR'])
    raw_output_file = os.path.join(output_dir, f'{filename_base}.txt')
    xml_output_file = os.path.join(output_dir, f'{filename_base}.xml')

    # Validate output directory
    if not validate_file_path(output_dir, current_app.config['OUTPUT_DIR']):
        return None, "Invalid output directory"

    # Add XML output path to command if needed (for nmap)
    if tool_id == 'nmap':
        if '-oX' not in options_list and '-oA' not in options_list:
            command_list_for_exec.extend(['-oX', xml_output_file])

    # Create the final command string
    command_for_display = ' '.join(quote_part(part) for part in command_list_for_exec)
    
    if not command_for_display or command_for_display.strip() == '':
        return None, "Generated command is empty"

    # Create the Task with all required fields
    new_task = Task()
    new_task.tool_id = tool_id
    new_task.project_id = project_id
    new_task.status = 'pending'
    new_task.original_target = target_or_query if tool_id == 'nmap' else None
    new_task.command = command_for_display
    new_task.raw_output_file = raw_output_file
    if tool_id == 'nmap':
        new_task.xml_output_file = xml_output_file
    else:
        new_task.xml_output_file = None

    try:
        db.session.add(new_task)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return None, f"Database error: {str(e)}"
    
    return new_task.id, None    

def add_single_task_to_queue(tool_id, target, options, project_id):
    """
    Creates a single task record and adds it to the persistent database queue.
    """
    # Validate inputs
    if not validate_tool_id(tool_id):
        return None, f"Invalid tool ID: {tool_id}"
    
    if not validate_target(target):
        return None, f"Invalid target: {target}"
    
    # Sanitize options
    options = sanitize_command_options(options)
    
    task_id, err = _create_task_record(tool_id, target, options, project_id)
    if err:
        return None, err
    
    # Add to the persistent database queue
    job_id = add_job_to_queue('single_task', {'task_id': task_id}, project_id=project_id)
    if job_id:
        return task_id, None
    else:
        return None, "Failed to add task to queue"

def add_project_scan_to_queue(tool_id, options, project_id):
    """
    Creates a task for every target in the project and adds them to the queue.
    """
    from app.models import Project
    
    # Validate tool_id
    if not validate_tool_id(tool_id):
        return 0, f"Invalid tool ID: {tool_id}"
    
    # Sanitize options
    options = sanitize_command_options(options)
    
    project = Project.query.get(project_id)
    if not project:
        return 0, "Project not found"
        
    targets = project.targets.all()
    if not targets:
        return 0, "Project has no targets"

    tasks_added = 0
    for target in targets:
        # Validate each target
        if validate_target(target.value):
            task_id, err = add_single_task_to_queue(tool_id, target.value, options, project_id)
            if not err:
                tasks_added += 1
        else:
            print(f"Warning: Skipping invalid target: {target.value}")
            
    return tasks_added, None

def add_playbook_to_queue(playbook_id, project_id, priority=0):
    """
    Add a playbook job to the persistent database queue.
    """
    # Validate playbook_id
    if not isinstance(playbook_id, str) or len(playbook_id) > 64:
        return None, "Invalid playbook ID"
    
    # Validate priority
    if not isinstance(priority, int) or priority < 0 or priority > 100:
        return None, "Invalid priority value"
    
    job_data = {
        'playbook_id': playbook_id,
        'project_id': project_id
    }
    
    job_id = add_job_to_queue('playbook', job_data, priority)
    if job_id:
        return job_id, None
    else:
        return None, "Failed to add playbook to queue"