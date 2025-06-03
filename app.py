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
import nmap # For Nmap XML parsing (pip install python-nmap)

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = secrets.token_hex(16)

# --- Application Configuration ---
TOOLS = {
    'nmap': {
        'name': 'Nmap',
        'description': 'Network scanner for discovering hosts and services',
        'command': 'nmap {target} {options}',
        'default_options': '-v -sV', # -sV for version detection. XML gives more if -A is used.
        'help_text': 'Target can be IP address, hostname, or subnet (e.g., 192.168.1.1, example.com, 192.168.1.0/24). Use -A for OS detection and more script output for richer XML.'
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
        'nmap': '-A -p 135,445 -T4', # Changed to -T4 from -T5, -A implies -sV and OS detection
    },
    'medium': {
        'nmap': '-sV -p- -T4 --min-rate=1000', # Common fast full port TCP scan with version
    },
    'high': {
        'nmap': '-A -p- -T4 --min-rate=1000', # -A for comprehensive, all TCP ports
    }
}

FOLLOW_UP_ACTIONS = {
    'searchsploit_version': {
        'name': 'SearchSploit Version',
        'tool_id': 'searchsploit',
        'query_format': '{service} {version}',
        'default_options': '--nmap'
    },
    'searchsploit_service': {
        'name': 'SearchSploit Service',
        'tool_id': 'searchsploit',
        'query_format': '{service}',
        'default_options': ''
    },
    'searchsploit_cpe': { # New follow-up for CPE
        'name': 'SearchSploit CPE',
        'tool_id': 'searchsploit',
        'query_format': '{cpe}', # Assumes CPE string can be directly searched
        'default_options': ''
    }
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
        # Output directory creation is primarily handled in _create_and_start_task,
        # especially for Nmap XML. Keep here as a fallback or for non-Nmap tools.
        os.makedirs('output', exist_ok=True)
        output_file = f"output/{task_id}.txt" # For raw text output

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
            for line_str in process.stdout:
                try:
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
            # If Nmap and it failed, it might not have produced a complete XML.
            # Check if XML file exists and is non-empty, otherwise log.
            if TASKS[task_id]['tool_id'] == 'nmap' and TASKS[task_id].get('xml_output_file'):
                xml_path = TASKS[task_id]['xml_output_file']
                if not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0:
                    TASKS[task_id]['recent_output'].append(f"[Warning: Nmap failed and XML output '{xml_path}' may be missing or incomplete.]")
                    app.logger.warning(f"Nmap task {task_id} failed and XML output '{xml_path}' might be missing/incomplete.")


        with open(output_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "-" * 50 + "\n")
            f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Status: {TASKS[task_id]['status']}\n")

    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        output_file = f"output/{task_id}.txt"
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\nERROR IN run_tool: {str(e)}\n")
        except:
            pass
        TASKS[task_id]['recent_output'].append(f"ERROR IN run_tool: {str(e)}")


def _create_and_start_task(tool_id, target_or_query, options_str):
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'

    if not target_or_query:
        if tool_id in ['nmap', 'sqlmap', 'dirb', 'curl', 'searchsploit']:
             return None, f'{TOOLS[tool_id]["name"]} query/target is required'

    tool_config = TOOLS[tool_id]
    task_id_str = f"{tool_id}_{int(time.time())}"
    os.makedirs('output', exist_ok=True) # Ensure output dir exists early

    xml_output_file_path = None
    final_options_str = options_str

    if tool_id == 'nmap':
        xml_output_file_path = f"output/{task_id_str}.xml"
        # Add -oX if not present. Avoid adding if -oA is present as -oA includes XML.
        if '-oX' not in final_options_str and '-oA' not in final_options_str:
            final_options_str = f"-oX {xml_output_file_path} {final_options_str}"
        elif '-oX' in final_options_str and xml_output_file_path not in final_options_str:
            # User might have specified their own -oX, log a warning or try to override.
            # For simplicity, we'll assume our -oX is the one we need for parsing.
            # This could be made more robust by parsing existing options.
            app.logger.warning(f"User provided -oX in options for Nmap task {task_id_str}. Ensuring our XML path is used.")
            # A more complex regex replace or option parsing would be needed here if we want to replace user's -oX.
            # For now, if user specified -oX some_other_file.xml, our parser might fail if it relies on output/{task_id_str}.xml
            # Safest is to prepend ours if not -oA
            if '-oA' not in final_options_str:
                 final_options_str = f"-oX {xml_output_file_path} {final_options_str}"


    if '{target}' in tool_config['command']:
        command = tool_config['command'].format(target=target_or_query, options=final_options_str)
    elif '{query}' in tool_config['command']:
        command = tool_config['command'].format(query=target_or_query, options=final_options_str)
    else:
        return None, 'Tool command format is invalid (missing {target} or {query})'

    if ';' in command or '&&' in command or '||' in command:
        pass

    TASKS[task_id_str] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None,
        'original_target': target_or_query if tool_id == 'nmap' else None,
        'xml_output_file': xml_output_file_path if tool_id == 'nmap' else None
    }
    thread = threading.Thread(target=run_tool, args=(task_id_str, command))
    thread.daemon = True
    thread.start()
    return task_id_str, None


# --- Main Application Routes (index, tool_page, run, list_tasks, task_details_output_part) are similar ---
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    # Pass tools to index.html if it needs them, or remove if not used by index.html directly
    return render_template('index.html', tools=TOOLS if 'username' not in session else None)


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
    target_or_query = request.form.get('target', '')
    if not target_or_query:
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
            with open(output_file, 'r', encoding='utf-8') as f:
                output_content = f.read()
            output_content = output_content.replace('<', '&lt;').replace('>', '&gt;')
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
            time.sleep(0.5) # Give it a moment to terminate gracefully
            if task_info['process'].poll() is None: # If still running
                task_info['process'].kill() # Force kill
            task_info['status'] = 'stopped'
            return jsonify({'status': 'success', 'message': 'Task stopped'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error stopping task: {str(e)}'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Task is not running or process not found'}), 400


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
        flash(f'No tools configured for intensity: {intensity}. Using default Nmap scan.', 'warning')
        # Fallback to a default Nmap scan if intensity config is missing tools
        tool_config_map = {'nmap': TOOLS['nmap']['default_options']}


    task_ids = []
    for tool_id, tool_specific_options in tool_config_map.items():
        if tool_id not in TOOLS:
            flash(f"Warning: Tool '{tool_id}' in intensity config but not in main TOOLS list.", 'warning')
            continue
        created_task_id, error_message = _create_and_start_task(tool_id, target, tool_specific_options)
        if error_message:
            flash(f"Could not start {TOOLS.get(tool_id, {}).get('name', tool_id)}: {error_message}", 'danger')
            continue
        if created_task_id:
            task_ids.append(created_task_id)
        else:
            flash(f"An unknown error occurred while starting {TOOLS.get(tool_id, {}).get('name', tool_id)}.", 'danger')

    if not task_ids:
        flash('No tasks could be started. Please check the configuration or logs.', 'danger')
        return redirect(url_for('home'))
    flash(f'Successfully started {len(task_ids)} scan(s). View them in the tasks list.', 'success')
    return redirect(url_for('list_tasks'))


# --- Nmap Parsing and Analysis Routes ---

def parse_nmap_output_simple(output_content):
    # This function remains as a fallback
    parsed_data = {"hosts": []}
    current_host = None
    host_regex = re.compile(r"Nmap scan report for (.*?) ?(?:\((.*?)\))?")
    port_service_regex = re.compile(
        r"(\d+)\/(tcp|udp)\s+(open)\s+([a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)?)\s*(.*)"
    )
    current_host_info = None
    for line in output_content.splitlines():
        host_match = host_regex.search(line)
        if host_match:
            if current_host_info:
                parsed_data["hosts"].append(current_host_info)
            hostname = host_match.group(1).strip()
            ip_address = host_match.group(2).strip() if host_match.group(2) else hostname
            if ip_address == hostname and not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                ip_address = "N/A" # Simplified
            current_host_info = {"host": hostname, "ip": ip_address, "ports": []}
            continue
        if current_host_info:
            service_match = port_service_regex.match(line.strip())
            if service_match:
                port = service_match.group(1)
                protocol = service_match.group(2)
                service = service_match.group(4).strip()
                version_info = service_match.group(5).strip()
                if "syn-ack" in version_info or " সুন্নত" in version_info:
                    version_info = ""
                current_host_info["ports"].append({
                    "port": port, "protocol": protocol, "service": service, "version": version_info
                })
    if current_host_info:
        parsed_data["hosts"].append(current_host_info)
    return parsed_data


def parse_nmap_xml_python_nmap(xml_file_path):
    """
    Parses Nmap XML output using the python-nmap library.
    """
    nm = nmap.PortScanner()
    parsed_data = {"hosts": []}
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        if not xml_content.strip():
            app.logger.warning(f"Nmap XML file {xml_file_path} is empty.")
            return {"hosts": [], "error": "Nmap XML file is empty."}

        scan_result = nm.analyse_nmap_xml_scan(xml_content)
        
        if not nm.all_hosts():
            app.logger.warning(f"python-nmap parsing yielded no hosts from {xml_file_path}. Scan stats: {nm.scanstats()}")
            # Check if scanstats has an error message
            if nm.scanstats().get('error', '').lower() == 'true':
                 errormsg = nm.scanstats().get('errormsg', 'Unknown Nmap execution error indicated in XML.')
                 return {"hosts": [], "error": f"Nmap error from XML: {errormsg}"}
            return parsed_data # Return empty if no hosts

        for host_ip in nm.all_hosts():
            host_info = nm[host_ip]
            current_host_data = {
                "host": host_info.hostname() if host_info.hostname() and host_info.hostname() != host_ip else host_ip,
                "ip": host_ip,
                "status": host_info.state(),
                "ports": [],
                "osmatch": [],
                "host_cpes": [] # Store host-level CPEs
            }

            # OS Detection
            if 'osmatch' in host_info and host_info['osmatch']:
                for osmatch in host_info['osmatch']:
                    os_details = {
                        "name": osmatch.get('name', 'N/A'),
                        "accuracy": osmatch.get('accuracy', 'N/A'),
                        "cpe": []
                    }
                    if 'osclass' in osmatch:
                        for osclass_entry in osmatch.get('osclass', []): # Ensure osclass is a list
                            if isinstance(osclass_entry, dict) and 'cpe' in osclass_entry and osclass_entry['cpe']:
                                for cpe_item in osclass_entry['cpe']: # CPE itself can be a list
                                     if cpe_item and cpe_item not in os_details["cpe"]:
                                        os_details["cpe"].append(cpe_item)
                                     if cpe_item and cpe_item not in current_host_data["host_cpes"]:
                                        current_host_data["host_cpes"].append(cpe_item)

                    current_host_data["osmatch"].append(os_details)
            
            # Port Information
            for proto in host_info.all_protocols():
                if proto not in ['tcp', 'udp']: continue # Focus on most common for now
                
                ports_on_proto = host_info[proto].keys()
                for port_num in ports_on_proto:
                    port_details = host_info[proto][port_num]
                    if port_details.get('state', 'N/A') == "open": # Only care about open ports for analysis
                        service_info = {
                            "port": str(port_num),
                            "protocol": proto,
                            "state": port_details.get('state', 'N/A'),
                            "service": port_details.get('name', 'N/A'),
                            "version": port_details.get('version', ''),
                            "product": port_details.get('product', ''),
                            "extrainfo": port_details.get('extrainfo', ''),
                            "cpe": port_details.get('cpe', '') 
                        }
                        current_host_data["ports"].append(service_info)
            
            parsed_data["hosts"].append(current_host_data)
            
    except FileNotFoundError:
        app.logger.error(f"Nmap XML file not found: {xml_file_path}")
        return {"hosts": [], "error": "Nmap XML file not found"}
    except nmap.PortScannerError as e: # This can catch XML parsing errors from python-nmap
        app.logger.error(f"python-nmap parsing error for {xml_file_path}: {str(e)}")
        return {"hosts": [], "error": f"Nmap XML parsing error: {str(e)}"}
    except Exception as e:
        app.logger.error(f"Unexpected error parsing Nmap XML {xml_file_path}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return {"hosts": [], "error": f"Unexpected Nmap XML parsing error: {str(e)}"}
        
    return parsed_data


@app.route('/task/<task_id>/analyze_nmap', methods=['GET'])
@login_required
def analyze_nmap_task(task_id):
    if task_id not in TASKS:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    task_info = TASKS[task_id]
    if task_info['tool_id'] != 'nmap':
        return jsonify({'status': 'error', 'message': 'Analysis is only available for Nmap tasks'}), 400

    xml_file_path = task_info.get('xml_output_file')
    
    if not xml_file_path or not os.path.exists(xml_file_path) or os.path.getsize(xml_file_path) == 0:
        # Fallback to text parsing if XML not found, empty, or not specified
        warning_msg = ""
        if not xml_file_path:
            warning_msg = "XML output path not recorded for this task. "
        elif not os.path.exists(xml_file_path):
            warning_msg = f"Nmap XML file '{xml_file_path}' not found. "
        elif os.path.getsize(xml_file_path) == 0:
            warning_msg = f"Nmap XML file '{xml_file_path}' is empty. "
        
        app.logger.warning(f"{warning_msg}Task {task_id}: Falling back to text parsing.")
        
        output_file = f"output/{task_id}.txt"
        if not os.path.exists(output_file):
            return jsonify({'status': 'error', 'message': 'Nmap output file (both XML and TXT) not found'}), 404
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                output_content = f.read()
            header_end_marker = "-" * 50 + "\n"
            if header_end_marker in output_content:
                # Skip header
                output_content = output_content.split(header_end_marker, 1)[-1]
                # Skip footer
                footer_start_marker = "\n" + "-" * 50 + "\nFinished:"
                if footer_start_marker in output_content:
                    output_content = output_content.split(footer_start_marker, 1)[0]

            parsed_data = parse_nmap_output_simple(output_content)
            if not parsed_data.get("hosts"):
                 parsed_data["warning"] = warning_msg + "Text parsing also yielded limited results."
            else:
                 parsed_data["warning"] = warning_msg + "Showing results from text parsing."
            return jsonify({'status': 'success', 'data': parsed_data, 'source': 'text'})
        except Exception as e:
            app.logger.error(f"Error during fallback text parsing for Nmap task {task_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error parsing Nmap text output: {str(e)}'}), 500

    # Proceed with XML parsing
    try:
        parsed_data = parse_nmap_xml_python_nmap(xml_file_path)
        if parsed_data.get("error"):
            # If parser itself found an error (e.g. file empty, nmap error in XML)
            return jsonify({'status': 'error', 'message': parsed_data["error"], 'data': parsed_data, 'source': 'xml_error'}), 500
        
        if not parsed_data.get("hosts") and "error" not in parsed_data:
             parsed_data["warning"] = "Nmap XML parsed, but no actionable host data was extracted. The scan might have found no live hosts or open ports."
        
        return jsonify({'status': 'success', 'data': parsed_data, 'source': 'xml'})
    except Exception as e:
        app.logger.error(f"Critical error calling parse_nmap_xml_python_nmap for {task_id}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'Critical error during Nmap XML processing: {str(e)}'}), 500


@app.route('/task/run_follow_up', methods=['POST'])
@login_required
def run_follow_up_action():
    data = request.json
    action_id = data.get('action_id')
    service_info = data.get('service_info') # {port, protocol, service, version, cpe, host_ip}
    original_nmap_target = data.get('original_nmap_target')

    if not all([action_id, service_info, original_nmap_target]): # original_nmap_target is crucial
        return jsonify({'status': 'error', 'message': 'Missing required parameters for follow-up action.'}), 400

    if action_id not in FOLLOW_UP_ACTIONS:
        return jsonify({'status': 'error', 'message': 'Invalid follow-up action ID.'}), 400

    action_config = FOLLOW_UP_ACTIONS[action_id]
    follow_up_tool_id = action_config['tool_id']
    
    # Construct the query/target for the follow-up tool
    try:
        # Ensure all expected keys exist in service_info, providing defaults
        query_params = {
            'service': service_info.get('service', ''),
            'version': service_info.get('version', ''),
            'port': service_info.get('port', ''),
            'protocol': service_info.get('protocol', ''),
            'target_host': original_nmap_target, # This is the overall target Nmap was run against
            'cpe': service_info.get('cpe', ''), # Added CPE
            'specific_host_ip': service_info.get('host_ip', original_nmap_target) # IP of the specific host from Nmap results
        }
        query_or_target = action_config['query_format'].format(**query_params).strip()

    except KeyError as e:
        return jsonify({'status': 'error', 'message': f'Error formatting query for follow-up: missing key {e}'}), 400
    
    if not query_or_target and action_id != 'some_action_that_needs_no_query': # Check if query is empty after formatting
        return jsonify({'status': 'error', 'message': f'Generated query for {action_config["name"]} is empty. Check data.'}), 400


    options_str = action_config.get('default_options', '')

    # For tools like Nmap or SQLMap in follow-ups, the target might be the specific_host_ip
    # For SearchSploit, it's a query. This logic is now handled by query_format.
    
    created_task_id, error_message = _create_and_start_task(
        follow_up_tool_id,
        query_or_target, # This is the formatted string
        options_str
    )

    if error_message:
        return jsonify({'status': 'error', 'message': error_message}), 400
    if not created_task_id:
        return jsonify({'status': 'error', 'message': 'Follow-up task creation failed.'}), 500

    return jsonify({
        'status': 'success',
        'message': f'Started follow-up: {TOOLS[follow_up_tool_id]["name"]} for "{query_or_target}"',
        'task_id': created_task_id
    })


# --- Main Entry Point ---
if __name__ == '__main__':
    # Ensure output directory exists on startup, though individual functions also check
    os.makedirs('output', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)