# /S2E/app/tasks/task_manager.py
# NEW FILE: A simple, in-memory task queue and worker manager.

import threading
import time
from collections import deque
import subprocess
from datetime import datetime
import os
import json
import shlex

from app.models import db, Task, Target
from app.scanner.parsers import parse_nmap_xml_for_services

# --- In-Memory Queue and Global State ---
# deque is a thread-safe list-like object, perfect for a simple queue.
TASK_QUEUE = deque()
QUEUE_LOCK = threading.Lock()
_APP = None


def run_tool_process(task_id):
    """
    UPDATED: Uses shlex.split to correctly handle paths with spaces.
    """
    task = Task.query.get(task_id)
    if not task:
        print(f"FATAL: Task {task_id} not found in DB for worker.")
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
    
    task.status = 'running'
    db.session.commit()

    try:
        os.makedirs(os.path.dirname(raw_output_file), exist_ok=True)
        with open(raw_output_file, 'w', encoding='utf-8') as f:
            f.write(f"Command: {task.command}\n")
            f.write(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write("-" * 50 + "\n\n")

        process = subprocess.Popen(
            command_list, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, universal_newlines=True, encoding='utf-8', errors='replace'
        )
        task.pid = process.pid
        db.session.commit()

        with open(raw_output_file, 'a', encoding='utf-8') as f:
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
    from app.scanner.services import _create_task_record
    
    playbook_id = playbook_job['playbook_id']
    project_id = playbook_job['project_id']

    # 1. Load the Playbook Definition
    playbooks_path = os.path.join(_APP.config['CONFIG_DIR'], 'playbooks.json')
    try:
        with open(playbooks_path, 'r') as f:
            playbook_def = next((p for p in json.load(f)["PLAYBOOKS"] if p["id"] == playbook_id), None)
    except FileNotFoundError:
        print(f"CRITICAL: playbooks.json not found.")
        return
        
    if not playbook_def:
        print(f"Error: Playbook '{playbook_id}' not defined.")
        return

    # 2. Run the Trigger Scan
    print(f"Playbook '{playbook_id}': Running trigger scan...")
    trigger_def = playbook_def['trigger']
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
            services_found = parse_nmap_xml_for_services(completed_task.xml_output_file)
            print(f"Playbook: Found {len(services_found)} services on {target.value}")
            all_found_services.extend(services_found)

    # 4. Apply Rules and Queue New Tasks
    print(f"Playbook '{playbook_id}': Trigger scans complete. Applying {len(playbook_def['rules'])} rules to {len(all_found_services)} found services...")
    tasks_queued = 0
    for service in all_found_services:
        for rule in playbook_def['rules']:
            # Check if the found service name matches any in the rule's list
            if any(rule_service in service['service_name'] for rule_service in rule['on_service']):
                action = rule['action']
                
                # Replace placeholders in the action's options
                options = action['options'].format(
                    host=service['host'],
                    port=service['port'],
                    protocol=service['protocol']
                )
                
                # The target for the new tool is often the host itself
                target_for_action = service['host']

                # Create and queue the new task
                new_task_id, err = _create_task_record(
                    action['tool_id'], target_for_action, options, project_id
                )
                if new_task_id:
                    with QUEUE_LOCK:
                        TASK_QUEUE.append({'type': 'single_task', 'task_id': new_task_id})
                    tasks_queued += 1
                    print(f"  - Queued '{action['name']}' for {service['host']}:{service['port']}")
                break # Move to the next service once a rule has matched

    print(f"Playbook '{playbook_id}': Finished. Queued {tasks_queued} new follow-up tasks.")


def task_manager_worker():
    """The main worker function for our background thread."""
    with _APP.app_context():
        while True:
            job = None
            with QUEUE_LOCK:
                if TASK_QUEUE:
                    job = TASK_QUEUE.popleft()
            if job:
                print(f"Task manager picked up job: {job}")
                if job['type'] == 'single_task':
                    run_tool_process(job['task_id'])
                elif job['type'] == 'playbook':
                    handle_playbook(job)
            time.sleep(2)

def start_task_manager(app):
    """Starts the background manager thread."""
    global _APP
    _APP = app
    manager_thread = threading.Thread(target=task_manager_worker)
    manager_thread.daemon = True
    manager_thread.start()
    print("Task manager thread started.")