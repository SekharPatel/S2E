from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import subprocess
import threading
import json
import time
import secrets
from datetime import datetime
from functools import wraps
import re # For Nmap parsing

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = secrets.token_hex(16)

# --- Application Configuration ---
TOOLS = {
    'nmap': {
        'name': 'Nmap',
        'description': 'Network scanner for discovering hosts and services',
        'command': 'nmap {target} {options}',
        'default_options': '-v -sV', # Added -sV for version detection by default
        'help_text': 'Target can be IP address, hostname, or subnet (e.g., 192.168.1.1, example.com, 192.168.1.0/24). Ensure -sV for version detection for analysis.'
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
    'curl': {
        'name': 'curl',
        'description': 'curl tool',
        'command': 'curl {target} {options}',
        'default_options': '',
        'help_text': 'Target should be the IP address or hostname to curl'
    }
}

INTENSITY_TOOL_CONFIG = {
    'low': {
        'nmap': '-A -p 135,445 -T5', # Consider if -sV should be default here too for analysis
        # 'curl': 'google.com',
    },
    'medium': {
        'nmap': '-p 4,5,6 -T4 -sV', # Added -sV
    },
    'high': {
        'nmap': '7,8,9', # -A includes -sV
        # 'ping': 'facebook.com',
    }
}

# FOLLOW_UP_ACTIONS: Defines tools that can be run as follow-up actions from analysis.
# Each entry specifies:
#   - name: Display name for the action button.
#   - tool_id: The key from the main TOOLS dictionary.
#   - query_format: How to construct the 'target' or 'query' for the follow-up tool.
#     Placeholders: {service}, {version}, {port}, {protocol}, {target_host} (original scan target)
#   - default_options: Specific options for this follow-up context.
FOLLOW_UP_ACTIONS = {
    'searchsploit_version': {
        'name': 'SearchSploit Version',
        'tool_id': 'searchsploit',
        'query_format': '{service} {version}',
        'default_options': '--nmap' # Useful for SearchSploit when parsing Nmap XML, but we are using text
    },
    'searchsploit_service': {
        'name': 'SearchSploit Service',
        'tool_id': 'searchsploit',
        'query_format': '{service}',
        'default_options': ''
    }
    # Future:
    # 'metasploit_search_version': {
    #     'name': 'Search Metasploit (Version)',
    #     'tool_id': 'msfconsole_search', # Assuming a new tool definition for msfconsole interactions
    #     'query_format': 'search {service} {version}',
    #     'default_options': '-q -x' # Example for msfconsole scripting
    # }
}


TASKS = {}
USERS = {'admin': 'securepassword123'}

# --- Authentication ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/home', methods=['GET'])
@login_required
def home():
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Tool Execution Logic ---
def run_tool(task_id, command):
    try:
        os.makedirs('output', exist_ok=True)
        output_file = f"output/{task_id}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Command: {command}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 50 + "\n")

        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, universal_newlines=False, encoding='utf-8', errors='replace'
        )
        TASKS[task_id]['process'] = process
        TASKS[task_id]['status'] = 'running'

        with open(output_file, 'a', encoding='utf-8') as f:
            for line_str in process.stdout: # Renamed line_bytes to line_str as Popen with encoding yields strings
                try:
                    # line_str is already a string because Popen was called with encoding='utf-8'
                    # No need to decode: line_bytes.decode('utf-8', errors='replace')
                    
                    cleaned_line_for_file = line_str 
                    cleaned_line_for_recent_output = line_str.strip()


                    f.write(cleaned_line_for_file)
                    TASKS[task_id]['recent_output'].append(cleaned_line_for_recent_output)
                    if len(TASKS[task_id]['recent_output']) > 100:
                        TASKS[task_id]['recent_output'].pop(0)
                except Exception as e:
                    error_msg = f"[Encoding/Processing Error: {str(e)}]\n"
                    f.write(error_msg)
                    TASKS[task_id]['recent_output'].append(error_msg.strip())


        return_code = process.wait()
        if return_code == 0:
            TASKS[task_id]['status'] = 'completed'
        else:
            TASKS[task_id]['status'] = 'failed'

        with open(output_file, 'a', encoding='utf-8') as f: # Ensure encoding for append
            f.write("\n" + "-" * 50 + "\n")
            f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Status: {TASKS[task_id]['status']}\n")
    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        output_file = f"output/{task_id}.txt" # Define here in case os.makedirs failed
        try: # Try to write error to file if possible
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\nERROR IN run_tool: {str(e)}\n")
        except: # If file writing fails, at least it's in TASKS
            pass
        TASKS[task_id]['recent_output'].append(f"ERROR IN run_tool: {str(e)}")


def _create_and_start_task(tool_id, target_or_query, options_str): # Renamed target to target_or_query
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'

    if not target_or_query: # Can be empty for some tools if options provide all
        # For specific tools like searchsploit, query is essential.
        # This check can be made more specific if needed.
        if tool_id in ['nmap', 'sqlmap', 'dirb', 'curl', 'searchsploit']: # Added searchsploit
             return None, f'{TOOLS[tool_id]["name"]} query/target is required'


    tool_config = TOOLS[tool_id]

    # Differentiate between tools that use 'target' and 'query' in their command string
    if '{target}' in tool_config['command']:
        command = tool_config['command'].format(target=target_or_query, options=options_str)
    elif '{query}' in tool_config['command']:
        command = tool_config['command'].format(query=target_or_query, options=options_str)
    else:
        return None, 'Tool command format is invalid (missing {target} or {query})'


    if ';' in command or '&&' in command or '||' in command: # Basic check
        # Allow for nmap scripts with ; if they are part of options and not target
        # This sanitization needs to be more robust for a production system
        # For now, we assume options are "safer"
        # A better way is to pass command and args as a list to Popen, not shell=True
        pass

    task_id_str = f"{tool_id}_{int(time.time())}"
    TASKS[task_id_str] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None,
        'original_target': target_or_query if tool_id == 'nmap' else None # Store original Nmap target
    }
    thread = threading.Thread(target=run_tool, args=(task_id_str, command))
    thread.daemon = True
    thread.start()
    return task_id_str, None


# --- Main Application Routes ---
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template('index.html', tools=TOOLS)

@app.route('/tool/<tool_id>')
@login_required
def tool_page(tool_id):
    if tool_id not in TOOLS:
        return redirect(url_for('index'))
    tool = TOOLS[tool_id].copy()
    if 'default_options' not in tool:
        tool['default_options'] = ''
    return render_template('tool.html', tool=tool, tool_id=tool_id)

@app.route('/run', methods=['POST'])
@login_required
def run():
    tool_id = request.form.get('tool_id')
    target_or_query = request.form.get('target', '') # Use 'target' as the generic form field name
    if not target_or_query: # If 'target' is empty, check if 'query' was sent (e.g. for searchsploit)
        target_or_query = request.form.get('query', '')

    options_from_form = request.form.get('options', '')
    tool_options_str = options_from_form if options_from_form else TOOLS.get(tool_id, {}).get('default_options', '')

    created_task_id, error_message = _create_and_start_task(tool_id, target_or_query, tool_options_str)

    if error_message:
        return jsonify({'status': 'error', 'message': error_message}), 400
    if not created_task_id:
        return jsonify({'status': 'error', 'message': 'Task creation failed'}), 500

    tool_config = TOOLS[tool_id]
    return jsonify({
        'status': 'success',
        'message': f'Started {tool_config["name"]}',
        'task_id': created_task_id
    })

@app.route('/tasks')
@login_required
def list_tasks():
    task_list = []
    for task_id_iter, task_info in TASKS.items():
        serializable_task = {
            'task_id': task_id_iter,
            'tool_id': task_info['tool_id'],
            'tool_name': TOOLS[task_info['tool_id']]['name'],
            'command': task_info['command'],
            'start_time': task_info['start_time'],
            'status': task_info['status'],
        }
        task_list.append(serializable_task)
    task_list.sort(key=lambda x: x['start_time'], reverse=True)
    return render_template('tasks.html', tasks=task_list)

@app.route('/task/<task_id>')
@login_required
def task_details(task_id):
    if task_id not in TASKS:
        return redirect(url_for('list_tasks'))
    task_info = TASKS[task_id]
    tool_name = TOOLS[task_info['tool_id']]['name']
    output_content = ""
    output_file = f"output/{task_id}.txt"
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f: # Ensure UTF-8
                output_content = f.read()
            output_content = output_content.replace('<', '&lt;').replace('>', '&gt;')
        except Exception as e:
            output_content = f"Error reading output: {str(e)}"
    
    # Determine if analysis tab should be shown
    show_analysis_tab = task_info.get('tool_id') == 'nmap'

    return render_template(
        'task_details.html',
        task_id=task_id,
        task=task_info,
        tool_name=tool_name,
        output=output_content,
        show_analysis_tab=show_analysis_tab, # Pass this to template
        follow_up_actions=FOLLOW_UP_ACTIONS # Pass follow-up actions for JS
    )

@app.route('/task/<task_id>/status')
@login_required
def task_status(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    task_info = TASKS[task_id]
    recent_output = task_info.get('recent_output', [])
    cleaned_output = []
    for line in recent_output:
        try:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='replace')
            cleaned_line = (line.strip()
                          .replace('<', '&lt;')
                          .replace('>', '&gt;'))
                          # Removed ASCII encoding here to preserve more characters
            cleaned_output.append(cleaned_line)
        except Exception as e:
            cleaned_output.append(f"[Error decoding output line: {str(e)}]")
    return jsonify({'status': task_info['status'], 'recent_output': cleaned_output})

@app.route('/task/<task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    task_info = TASKS[task_id]
    if task_info['status'] == 'running' and task_info['process']:
        try:
            task_info['process'].terminate()
            time.sleep(0.5)
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

@app.route('/home/scan', methods=['POST'])
@login_required
def home_scan():
    target = request.form.get('target')
    intensity = request.form.get('intensity', '')
    if not target:
        flash('Target is required.', 'danger')
        return redirect(url_for('home'))
    tool_config_map = INTENSITY_TOOL_CONFIG.get(intensity, {})
    if not tool_config_map:
        flash(f'No tools configured for intensity: {intensity}.', 'warning')
        return redirect(url_for('home'))
    task_ids = []
    for tool_id, tool_specific_options in tool_config_map.items():
        if tool_id not in TOOLS:
            flash(f"Warning: Tool '{tool_id}' in intensity config but not in main TOOLS list.", 'warning')
            continue
        # For home scan, the 'target' is always the Nmap target or similar.
        # If a tool like searchsploit were in INTENSITY_TOOL_CONFIG, its 'target' (query)
        # would need to be thoughtfully constructed or might not make sense here.
        # Assuming 'target' from form is suitable for all tools in INTENSITY_TOOL_CONFIG.
        created_task_id, error_message = _create_and_start_task(tool_id, target, tool_specific_options)
        if error_message:
            flash(f"Could not start {TOOLS.get(tool_id, {}).get('name', tool_id)}: {error_message}", 'danger')
            continue
        if created_task_id:
            task_ids.append(created_task_id)
        else: # Should be caught by error_message
            flash(f"An unknown error occurred while starting {TOOLS.get(tool_id, {}).get('name', tool_id)}.", 'danger')

    if not task_ids:
        flash('No tasks could be started. Please check the configuration or logs.', 'danger')
        return redirect(url_for('home'))
    flash(f'Successfully started {len(task_ids)} scan(s). View them in the tasks list.', 'success')
    return redirect(url_for('list_tasks'))


# --- Nmap Parsing and Analysis Routes ---

def parse_nmap_output_simple(output_content):
    """
    Parses Nmap text output to extract open ports, services, and versions.
    This is a simplified parser using regex. For robust parsing, Nmap's XML output (-oX)
    and a dedicated XML parsing library (like `python-nmap` or `xml.etree.ElementTree`) is recommended.
    """
    parsed_data = {"hosts": []}
    current_host = None

    # Regex to find "Host is up" lines and capture IP/hostname
    host_regex = re.compile(r"Nmap scan report for (.*?) ?(?:\((.*?)\))?")
    # Regex for open ports: "PORT STATE SERVICE VERSION"
    # Example: 22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0)
    # Example: 80/tcp open  http    nginx 1.14.0 (Ubuntu)
    # Example: 443/tcp open ssl/http Apache httpd 2.4.29 ((Ubuntu))
    port_service_regex = re.compile(
        r"(\d+)\/(tcp|udp)\s+(open)\s+([a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)?)\s*(.*)"
    )
    # Simpler regex if version is not always present or complex:
    # port_service_regex = re.compile(r"(\d+\/(?:tcp|udp))\s+open\s+([^\s]+)\s*(.*)")

    current_host_info = None

    for line in output_content.splitlines():
        host_match = host_regex.search(line)
        if host_match:
            if current_host_info: # Save previous host if any
                parsed_data["hosts"].append(current_host_info)

            hostname = host_match.group(1).strip()
            ip_address = host_match.group(2).strip() if host_match.group(2) else hostname
            if ip_address == hostname and not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address): # if hostname is not an IP
                # This logic might need refinement based on Nmap output variations
                ip_address = "N/A"


            current_host_info = {"host": hostname, "ip": ip_address, "ports": []}
            continue

        if current_host_info: # Only parse ports if we are under a host section
            service_match = port_service_regex.match(line.strip())
            if service_match:
                port = service_match.group(1)
                protocol = service_match.group(2)
                # state = service_match.group(3) # We are only interested in open
                service = service_match.group(4).strip()
                version_info = service_match.group(5).strip()

                # Basic version cleaning (can be improved)
                if "syn-ack" in version_info or " সুন্নত" in version_info: # ignore some noise
                    version_info = ""

                current_host_info["ports"].append({
                    "port": port,
                    "protocol": protocol,
                    "service": service,
                    "version": version_info
                })

    if current_host_info: # Append the last host scanned
        parsed_data["hosts"].append(current_host_info)

    return parsed_data


@app.route('/task/<task_id>/analyze_nmap', methods=['GET'])
@login_required
def analyze_nmap_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    task_info = TASKS[task_id]
    if task_info['tool_id'] != 'nmap':
        return jsonify({'status': 'error', 'message': 'Analysis is only available for Nmap tasks'}), 400

    output_file = f"output/{task_id}.txt"
    if not os.path.exists(output_file):
        return jsonify({'status': 'error', 'message': 'Output file not found'}), 404

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        # Remove the header part of the output file for cleaner parsing
        header_end_marker = "-" * 50 + "\n"
        if header_end_marker in output_content:
            output_content = output_content.split(header_end_marker, 1)[1]

        parsed_data = parse_nmap_output_simple(output_content)
        return jsonify({'status': 'success', 'data': parsed_data})
    except Exception as e:
        app.logger.error(f"Error parsing Nmap output for {task_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error parsing Nmap output: {str(e)}'}), 500


@app.route('/task/run_follow_up', methods=['POST'])
@login_required
def run_follow_up_action():
    data = request.json
    action_id = data.get('action_id')
    service_info = data.get('service_info') # {port, protocol, service, version}
    original_nmap_target = data.get('original_nmap_target') # The IP/host Nmap was run against

    if not all([action_id, service_info, original_nmap_target]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters for follow-up action.'}), 400

    if action_id not in FOLLOW_UP_ACTIONS:
        return jsonify({'status': 'error', 'message': 'Invalid follow-up action ID.'}), 400

    action_config = FOLLOW_UP_ACTIONS[action_id]
    follow_up_tool_id = action_config['tool_id']
    
    # Construct the query/target for the follow-up tool
    try:
        query_or_target = action_config['query_format'].format(
            service=service_info.get('service', ''),
            version=service_info.get('version', ''),
            port=service_info.get('port', ''),
            protocol=service_info.get('protocol', ''),
            target_host=original_nmap_target
        ).strip() # Strip to remove leading/trailing spaces if some fields are empty
    except KeyError as e:
        return jsonify({'status': 'error', 'message': f'Error formatting query for follow-up: missing key {e}'}), 400

    options_str = action_config.get('default_options', '')

    created_task_id, error_message = _create_and_start_task(
        follow_up_tool_id,
        query_or_target,
        options_str
    )

    if error_message:
        return jsonify({'status': 'error', 'message': error_message}), 400
    if not created_task_id:
        return jsonify({'status': 'error', 'message': 'Follow-up task creation failed.'}), 500

    return jsonify({
        'status': 'success',
        'message': f'Started follow-up task: {TOOLS[follow_up_tool_id]["name"]} with query "{query_or_target}"',
        'task_id': created_task_id
    })


# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)