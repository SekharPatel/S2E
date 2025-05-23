from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import subprocess
import threading
import json
import time
import secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key

# Configuration
TOOLS = {
    'nmap': {
        'name': 'Nmap',
        'description': 'Network scanner for discovering hosts and services',
        'command': 'nmap {target} {options}',
        'default_options': ' ',
        'help_text': 'Target can be IP address, hostname, or subnet (e.g., 192.168.1.1, example.com, 192.168.1.0/24)'
    },
    'searchsploit': {
        'name': 'SearchSploit',
        'description': 'Exploit-DB search tool',
        'command': 'searchsploit {query} {options}',
        'default_options': '',
        'help_text': 'Search for exploits by keyword or software version'
    },
    'sqlmap': {
        'name': 'SQLMap',
        'description': 'Automated SQL injection tool',
        'command': 'sqlmap -u {target} {options}',
        'default_options': '--batch',
        'help_text': 'Target should be a URL with a parameter (e.g., http://example.com/page.php?id=1)'
    },
    'dirb': {
        'name': 'Dirb',
        'description': 'Web content scanner',
        'command': 'dirb {target} {options}',
        'default_options': '',
        'help_text': 'Target should be the base URL (e.g., http://example.com/)'
    },
}

# Will store running tasks
TASKS = {}

# Authentication configuration (for demo purposes - in production use a proper authentication system)
USERS = {
    'admin': 'securepassword123',  # In a real app, store password hashes, not plaintext
}

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials. Please try again.'
    
    return render_template('login.html', error=error)

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Function to run command in background
def run_tool(task_id, command):
    try:
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        output_file = f"output/{task_id}.txt"
        
        # Log start time
        with open(output_file, 'w') as f:
            f.write(f"Command: {command}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 50 + "\n")
        
        # Execute command and capture output in real-time
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        
        TASKS[task_id]['process'] = process
        TASKS[task_id]['status'] = 'running'
        
        # Stream the output to file
        with open(output_file, 'a') as f:
            for line in process.stdout:
                f.write(line)
                # Also store recent output in memory for UI updates
                TASKS[task_id]['recent_output'].append(line.strip())
                if len(TASKS[task_id]['recent_output']) > 100:  # Keep only last 100 lines
                    TASKS[task_id]['recent_output'].pop(0)
        
        # Check return code
        return_code = process.wait()
        
        # Update task status based on return code
        if return_code == 0:
            TASKS[task_id]['status'] = 'completed'
        else:
            TASKS[task_id]['status'] = 'failed'
        
        # Log completion
        with open(output_file, 'a') as f:
            f.write("\n" + "-" * 50 + "\n")
            f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Status: {TASKS[task_id]['status']}\n")
            
    except Exception as e:
        # Handle exceptions
        TASKS[task_id]['status'] = 'error'
        with open(output_file, 'a') as f:
            f.write(f"\nERROR: {str(e)}\n")

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', tools=TOOLS)

@app.route('/tool/<tool_id>')
@login_required
def tool_page(tool_id):
    if tool_id not in TOOLS:
        return redirect(url_for('index'))
    
    # Ensure all expected keys are present in the tool dictionary
    tool = TOOLS[tool_id].copy()
    # Add empty default values for optional fields if they don't exist
    if 'default_options' not in tool:
        tool['default_options'] = ''
    
    return render_template('tool.html', tool=tool, tool_id=tool_id)

@app.route('/run', methods=['POST'])
@login_required
def run():
    tool_id = request.form.get('tool_id')
    target = request.form.get('target', '')
    options = request.form.get('options', '')
    
    if not tool_id or tool_id not in TOOLS:
        return jsonify({'status': 'error', 'message': 'Invalid tool selected'}), 400
    
    if not target:
        return jsonify({'status': 'error', 'message': 'Target is required'}), 400
    
    # Prepare command
    tool_config = TOOLS[tool_id]
    command = tool_config['command'].format(
        target=target,
        options=options if options else tool_config.get('default_options', '')
    )
    
    # Sanitize input (basic validation - would need more robust validation in production)
    if ';' in command or '&&' in command or '||' in command:
        return jsonify({'status': 'error', 'message': 'Invalid characters in command'}), 400
    
    # Create task ID and info
    task_id = f"{tool_id}_{int(time.time())}"
    TASKS[task_id] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None
    }
    
    # Start the tool in a background thread
    thread = threading.Thread(target=run_tool, args=(task_id, command))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'success', 
        'message': f'Started {tool_config["name"]}', 
        'task_id': task_id
    })

@app.route('/tasks')
@login_required
def list_tasks():
    # Convert task info to JSON-serializable format
    task_list = []
    for task_id, task_info in TASKS.items():
        serializable_task = {
            'task_id': task_id,
            'tool_id': task_info['tool_id'],
            'tool_name': TOOLS[task_info['tool_id']]['name'],
            'command': task_info['command'],
            'start_time': task_info['start_time'],
            'status': task_info['status'],
        }
        task_list.append(serializable_task)
    
    # Sort by start time, newest first
    task_list.sort(key=lambda x: x['start_time'], reverse=True)
    
    return render_template('tasks.html', tasks=task_list)

@app.route('/task/<task_id>')
@login_required
def task_details(task_id):
    if task_id not in TASKS:
        return redirect(url_for('list_tasks'))
    
    task_info = TASKS[task_id]
    tool_name = TOOLS[task_info['tool_id']]['name']
    
    # Try to read full output from file
    output_content = ""
    output_file = f"output/{task_id}.txt"
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                output_content = f.read()
            # Clean the output for display
            output_content = output_content.replace('<', '&lt;').replace('>', '&gt;')
        except Exception as e:
            output_content = f"Error reading output: {str(e)}"
    
    return render_template(
        'task_details.html', 
        task_id=task_id, 
        task=task_info, 
        tool_name=tool_name,
        output=output_content
    )

@app.route('/task/<task_id>/status')
@login_required
def task_status(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    
    # Get the most recent output lines
    recent_output = task_info.get('recent_output', [])
    
    # Clean the output lines for display
    cleaned_output = []
    for line in recent_output:
        cleaned_line = line.replace('<', '&lt;').replace('>', '&gt;')
        cleaned_output.append(cleaned_line)
    
    response = {
        'status': task_info['status'],
        'recent_output': cleaned_output
    }
    
    return jsonify(response)

@app.route('/task/<task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    
    task_info = TASKS[task_id]
    
    if task_info['status'] == 'running' and task_info['process']:
        try:
            # Try to terminate the process
            task_info['process'].terminate()
            # Give it a moment to terminate gracefully
            time.sleep(0.5)
            # Force kill if still running
            if task_info['process'].poll() is None:
                task_info['process'].kill()
            
            task_info['status'] = 'stopped'
            return jsonify({'status': 'success', 'message': 'Task stopped'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error stopping task: {str(e)}'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Task is not running'}), 400

@app.route('/api/tools')
@login_required
def api_tools():
    return jsonify(TOOLS)

# Main entry point
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)