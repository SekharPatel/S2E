# /S2E/app/tasks/task_manager.py
# UPDATED: Replace in-memory queue with persistent SQLite-based queue system

import threading
import time
from datetime import datetime
import os
import json
import shlex
import subprocess

from app.models import db, Task, Target, JobQueue
from app.scanner.parsers import parse_nmap_xml_for_services
from app.utils.validation import validate_tool_id, sanitize_command_options, validate_file_path, ValidationError, validate_command_security

# --- Global State ---
_APP = None
_WORKER_RUNNING = False

def add_job_to_queue(job_type, job_data, priority=0, project_id=None):
    """
    Add a job to the persistent database queue.
    
    Args:
        job_type: 'single_task' or 'playbook'
        job_data: Dictionary containing job parameters
        priority: Integer priority (higher = more important)
        project_id: ID of the project this job belongs to (optional)
    """
    if _APP is None:
        print("Error: Task manager not initialized")
        return None
        
    # Validate job_type
    if job_type not in ['single_task', 'playbook']:
        print("Error: Invalid job type")
        return None
        
    try:
        with _APP.app_context():
            job = JobQueue()
            job.job_type = job_type
            job.priority = priority
            job.project_id = project_id
            job.set_job_data(job_data)
            db.session.add(job)
            db.session.commit()
            print(f"Added {job_type} job to queue with ID {job.id}")
            return job.id
    except Exception as e:
        print(f"Error adding job to queue: {e}")
        return None

def get_next_job():
    """
    Get the next pending job from the database queue.
    Returns the job with highest priority, then oldest created_at.
    """
    if _APP is None:
        print("Error: Task manager not initialized")
        return None
        
    try:
        with _APP.app_context():
            job = JobQueue.query.filter_by(status='pending').order_by(
                JobQueue.priority.desc(),
                JobQueue.created_at.asc()
            ).first()
            
            if job:
                # Mark as processing
                job.status = 'processing'
                job.started_at = datetime.utcnow()
                db.session.commit()
                print(f"Retrieved job {job.id} ({job.job_type}) from queue")
                return job
            return None
    except Exception as e:
        print(f"Error retrieving job from queue: {e}")
        return None

def mark_job_completed(job_id, success=True):
    """Mark a job as completed or failed."""
    if _APP is None:
        print("Error: Task manager not initialized")
        return
        
    try:
        with _APP.app_context():
            job = JobQueue.query.get(job_id)
            if job:
                job.status = 'completed' if success else 'failed'
                job.completed_at = datetime.utcnow()
                db.session.commit()
                print(f"Marked job {job_id} as {'completed' if success else 'failed'}")
    except Exception as e:
        print(f"Error marking job {job_id} as completed: {e}")

def run_tool_process(task_id):
    """
    UPDATED: Uses shlex.split to correctly handle paths with spaces.
    """
    if _APP is None:
        print("Error: Task manager not initialized")
        return None
        
    with _APP.app_context():
        task = Task.query.get(task_id)
        if not task:
            print(f"FATAL: Task {task_id} not found in DB for worker.")
            return None

        # Validate tool_id
        if not validate_tool_id(task.tool_id):
            print(f"Security error: Invalid tool_id: {task.tool_id}")
            task.status = 'error'
            db.session.commit()
            return None

        # Validate command security
        if not validate_command_security(task.command):
            print(f"Security error: Command contains dangerous patterns: {task.command}")
            task.status = 'error'
            db.session.commit()
            return None

        try:
            command_list = shlex.split(task.command)
            print(f"Executing command list: {command_list}")
        except ValueError as e:
            print(f"Error parsing command for task {task_id}: {e}")
            task.status = 'error'
            db.session.commit()
            return None
        
        raw_output_file = task.raw_output_file
        
        # Validate output file path
        if not validate_file_path(raw_output_file, _APP.config['OUTPUT_DIR']):
            print(f"Security error: Invalid output file path: {raw_output_file}")
            task.status = 'error'
            db.session.commit()
            return None
        
        task.status = 'running'
        db.session.commit()

        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(raw_output_file)
            os.makedirs(output_dir, exist_ok=True)
            
            with open(raw_output_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {task.command}\n")
                f.write(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write("-" * 50 + "\n\n")

            # Execute the command
            process = subprocess.Popen(
                command_list, 
                shell=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                bufsize=1, 
                universal_newlines=True, 
                encoding='utf-8', 
                errors='replace'
            )
            task.pid = process.pid
            db.session.commit()

            # Capture output
            with open(raw_output_file, 'a', encoding='utf-8') as f:
                if process.stdout:
                    for line in process.stdout:
                        f.write(line)

            return_code = process.wait()
            
            task.status = 'completed' if return_code == 0 else 'failed'

        except Exception as e:
            print(f"Error running task {task_id}: {e}")
            task.status = 'error'
        finally:
            task.pid = None
            db.session.commit()
            if os.path.exists(raw_output_file):
                with open(raw_output_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "-" * 50 + "\n")
                    f.write(f"Finished: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                    f.write(f"Status: {task.status}\n")

        return task

def handle_playbook(playbook_job):
    """
    The new playbook engine. It runs a trigger scan, then dynamically
    queues new tasks based on the results and the playbook's rules.
    """
    if _APP is None:
        print("Error: Task manager not initialized")
        return
        
    from app.scanner.services import _create_task_record
    
    playbook_id = playbook_job['playbook_id']
    project_id = playbook_job['project_id']

    # Validate playbook_id
    if not isinstance(playbook_id, str) or len(playbook_id) > 64:
        print(f"Security error: Invalid playbook_id: {playbook_id}")
        return

    # 1. Load the Playbook Definition
    playbooks_path = os.path.join(_APP.config['CONFIG_DIR'], 'playbooks.json')
    
    # Validate file path
    if not validate_file_path(playbooks_path, _APP.config['CONFIG_DIR']):
        print(f"Security error: Invalid playbooks path: {playbooks_path}")
        return
    
    try:
        with open(playbooks_path, 'r') as f:
            playbooks_data = json.load(f)
            playbook_def = next((p for p in playbooks_data["PLAYBOOKS"] if p["id"] == playbook_id), None)
    except FileNotFoundError:
        print(f"CRITICAL: playbooks.json not found.")
        return
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing playbooks.json: {e}")
        return
        
    if not playbook_def:
        print(f"Error: Playbook '{playbook_id}' not defined.")
        return

    # 2. Run the Trigger Scan
    print(f"Playbook '{playbook_id}': Running trigger scan...")
    trigger_def = playbook_def['trigger']
    
    # Validate trigger configuration
    if not isinstance(trigger_def, dict) or 'tool_id' not in trigger_def or 'options' not in trigger_def:
        print(f"Security error: Invalid trigger definition in playbook {playbook_id}")
        return
    
    # Sanitize trigger options
    trigger_def['options'] = sanitize_command_options(trigger_def['options'])
    
    with _APP.app_context():
        project_targets = Target.query.filter_by(project_id=project_id).all()
        if not project_targets:
            print(f"Playbook '{playbook_id}': No targets in project. Aborting.")
            return

        # For now, we assume the trigger runs on all targets.
        # A more advanced system could allow a single target trigger.
        all_found_services = []
        for target in project_targets:
            # Create and run the trigger task for one target
            task_id, err = _create_task_record(
                trigger_def['tool_id'], target.value, trigger_def['options'], project_id
            )
            if err:
                print(f"Playbook trigger error for {target.value}: {err}")
                continue
                
            # This is a blocking call. The manager waits for the scan to finish.
            completed_task = run_tool_process(task_id)

            # 3. Parse the Results
            if completed_task and completed_task.status == 'completed' and completed_task.xml_output_file:
                # Validate XML file path
                if validate_file_path(completed_task.xml_output_file, _APP.config['OUTPUT_DIR']):
                    services_found = parse_nmap_xml_for_services(completed_task.xml_output_file)
                    print(f"Playbook: Found {len(services_found)} services on {target.value}")
                    if services_found:
                        print(f"  Services found: {[f'{s['service_name']} on {s['host']}:{s['port']}' for s in services_found]}")
                    all_found_services.extend(services_found)
                else:
                    print(f"Security warning: Invalid XML file path: {completed_task.xml_output_file}")
            else:
                print(f"Playbook: Task {task_id} did not complete successfully or has no XML output")
                if completed_task:
                    print(f"  Task status: {completed_task.status}")
                    print(f"  XML output file: {completed_task.xml_output_file}")

        # 4. Apply Rules and Queue New Tasks
        print(f"Playbook '{playbook_id}': Trigger scans complete. Applying {len(playbook_def['rules'])} rules to {len(all_found_services)} found services...")
        tasks_queued = 0
        for service in all_found_services:
            for rule in playbook_def['rules']:
                # Validate rule structure
                if not isinstance(rule, dict) or 'on_service' not in rule or 'action' not in rule:
                    print(f"Security warning: Invalid rule structure in playbook {playbook_id}")
                    continue
                
                # Check if the found service name matches any in the rule's list
                if any(rule_service in service['service_name'] for rule_service in rule['on_service']):
                    action = rule['action']
                    
                    # Validate action structure
                    if not isinstance(action, dict) or 'options' not in action:
                        print(f"Security warning: Invalid action structure in playbook {playbook_id}")
                        continue
                    
                    try:
                        # Replace placeholders in the action's options
                        # Support both <protocol> and {protocol} style placeholders
                        action_options = action['options']
                        action_options = (action_options
                            .replace('<host>', '{host}')
                            .replace('<port>', '{port}')
                            .replace('<protocol>', '{protocol}')
                        )
                        
                        # Check if all required keys are present
                        required_keys = ['host', 'port', 'protocol']
                        missing_keys = [key for key in required_keys if key not in service]
                        if missing_keys:
                            print(f"Error: Missing required keys: {missing_keys}")
                            continue
                        
                        options = action_options.format(
                            host=service['host'],
                            port=service['port'],
                            protocol=service['protocol']
                        )
                        
                        # Sanitize the formatted options after placeholder replacement
                        options = sanitize_command_options(options)
                    except (KeyError, ValueError) as e:
                        print(f"Error formatting action options: {e}")
                        continue
                    
                    # The target for the new tool is often the host itself
                    target_for_action = service['host']

                    # Create and queue the new task
                    new_task_id, err = _create_task_record(
                        action['tool_id'], target_for_action, options, project_id
                    )
                    if new_task_id:
                        # Use the new database queue system
                        job_id = add_job_to_queue('single_task', {'task_id': new_task_id}, project_id=project_id)
                        if job_id:
                            tasks_queued += 1
                            print(f"  - Queued '{action['name']}' for {service['host']}:{service['port']}")
                        else:
                            print(f"Failed to add task to queue for {service['host']}:{service['port']}")
                    else:
                        print(f"Failed to create task: {err}")
                    break # Move to the next service once a rule has matched

        print(f"Playbook '{playbook_id}': Finished. Queued {tasks_queued} new follow-up tasks.")

def task_manager_worker():
    """
    The main worker function for our background thread.
    Now uses the persistent database queue instead of in-memory deque.
    """
    global _WORKER_RUNNING
    _WORKER_RUNNING = True
    
    print("Task manager worker started with persistent database queue")
    
    while _WORKER_RUNNING:
        try:
            job = get_next_job()
            if job:
                job_data = job.get_job_data()
                success = True
                
                print(f"Processing job {job.id}: {job.job_type}")
                
                if job.job_type == 'single_task':
                    task = run_tool_process(job_data['task_id'])
                    success = task is not None and task.status in ['completed', 'failed']  # Not 'error'
                elif job.job_type == 'playbook':
                    try:
                        handle_playbook(job_data)
                    except Exception as e:
                        print(f"Error handling playbook job {job.id}: {e}")
                        success = False
                
                mark_job_completed(job.id, success)
            else:
                # No jobs available, sleep a bit
                time.sleep(2)
                
        except Exception as e:
            print(f"Error in task manager worker: {e}")
            time.sleep(5)  # Sleep longer on errors

def start_task_manager(app):
    """
    Starts the background manager thread.
    On startup, checks for any jobs that were 'processing' when the app shut down
    and resets them to 'pending' for retry.
    """
    global _APP
    _APP = app
    
    # Recovery: Reset any jobs that were stuck in 'processing' state
    with app.app_context():
        stuck_jobs = JobQueue.query.filter_by(status='processing').all()
        for job in stuck_jobs:
            job.status = 'pending'
            job.started_at = None
            print(f"Reset stuck job {job.id} to pending")
        if stuck_jobs:
            db.session.commit()
            print(f"Reset {len(stuck_jobs)} stuck jobs to pending")
    
    manager_thread = threading.Thread(target=task_manager_worker)
    manager_thread.daemon = True
    manager_thread.start()
    print("Task manager thread started with persistent queue system.")

def stop_task_manager():
    """Stop the task manager worker gracefully."""
    global _WORKER_RUNNING
    _WORKER_RUNNING = False
    print("Task manager worker stopped.")

# Import re for regex patterns
import re