# /S2E/app/utils.py

from flask import current_app
import os, subprocess, threading
from datetime import datetime
import time
import re
import nmap
from . import TASKS


def run_tool(task_id, command, raw_output_file, app):
    """The target function for the scanning thread. Writes to a specific file."""
    with app.app_context():
        try:
            # Ensure the parent directory for the output file exists
            os.makedirs(os.path.dirname(raw_output_file), exist_ok=True)
            
            with open(raw_output_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")

            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, universal_newlines=False, encoding='utf-8', errors='replace'
            )
            TASKS[task_id]['process'] = process
            TASKS[task_id]['status'] = 'running'

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                for line_str in process.stdout:
                    TASKS[task_id]['recent_output'].append(line_str.strip())
                    if len(TASKS[task_id]['recent_output']) > 100:
                        TASKS[task_id]['recent_output'].pop(0)
                    f.write(line_str)
            
            return_code = process.wait()
            TASKS[task_id]['status'] = 'completed' if return_code == 0 else 'failed'

            if TASKS[task_id]['status'] == 'failed':
                xml_path = TASKS[task_id].get('xml_output_file')
                if xml_path and (not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0):
                    msg = f"[Warning: Nmap failed and XML output may be missing or incomplete.]"
                    TASKS[task_id]['recent_output'].append(msg)
                    current_app.logger.warning(f"Nmap task {task_id} failed: {msg}")

            with open(raw_output_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Status: {TASKS[task_id]['status']}\n")

        except Exception as e:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['recent_output'].append(f"ERROR IN run_tool: {str(e)}")
            current_app.logger.error(f"Error in run_tool for task {task_id}: {e}", exc_info=True)


def _create_and_start_task(tool_id, target_or_query, options_str):
    """Helper to create task dictionary, command, and start the thread with new directory structure."""
    TOOLS = current_app.config.get('TOOLS', {})
    OUTPUT_DIR = current_app.config['OUTPUT_DIR']
    
    if not tool_id or tool_id not in TOOLS:
        return None, 'Invalid tool selected'
    if not target_or_query and tool_id in ['nmap', 'sqlmap', 'dirb', 'curl', 'searchsploit']:
        return None, f'{TOOLS[tool_id]["name"]} query/target is required'

    tool_config = TOOLS[tool_id]
    task_id_str = f"{tool_id}_{int(time.time())}"
    
    # --- NEW: Path generation based on config ---
    formats = [f.strip() for f in tool_config.get('output_formats', 'raw').split(',')]
    tool_output_dir = os.path.join(OUTPUT_DIR, tool_id)
    
    raw_output_file_path = None
    xml_output_file_path = None

    if len(formats) > 1:
        # Multiple formats, use subdirectories
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, 'raw', f'{task_id_str}.txt')
        if 'xml' in formats:
            xml_output_file_path = os.path.join(tool_output_dir, 'xml', f'{task_id_str}.xml')
    else:
        # Single format, save directly in the tool's directory
        if 'raw' in formats:
            raw_output_file_path = os.path.join(tool_output_dir, f'{task_id_str}.txt')
    
    if not raw_output_file_path:
        # Fallback if config is weird, though it shouldn't happen
        return None, "Tool has no 'raw' output format defined in config."

    # Build the options string
    final_options = options_str
    default_opts = tool_config.get('default_options', '')
    if default_opts and default_opts not in final_options:
        final_options = f"{default_opts} {final_options}"
    
    # Add XML output flag for Nmap, ensuring it has a path
    if tool_id == 'nmap' and xml_output_file_path:
        os.makedirs(os.path.dirname(xml_output_file_path), exist_ok=True)
        if '-oX' not in final_options and '-oA' not in final_options:
            final_options = f"-oX \"{xml_output_file_path}\" {final_options}"

    command_params = {'target': target_or_query, 'query': target_or_query, 'options': final_options}
    command = tool_config['command'].format(**command_params)

    # Store the precise file paths in the task dictionary
    TASKS[task_id_str] = {
        'tool_id': tool_id,
        'command': command,
        'start_time': datetime.now().isoformat(),
        'status': 'starting',
        'recent_output': [],
        'process': None,
        'original_target': target_or_query if tool_id == 'nmap' else None,
        'raw_output_file': raw_output_file_path,
        'xml_output_file': xml_output_file_path
    }

    app = current_app._get_current_object()
    thread = threading.Thread(target=run_tool, args=(task_id_str, command, raw_output_file_path, app))
    thread.daemon = True
    thread.start()
    return task_id_str, None

def parse_nmap_output_simple(output_content):
    """
    Parses the raw text output of an Nmap scan. This is a fallback method.
    """
    parsed_data = {"hosts": []}
    current_host_info = None
    host_regex = re.compile(r"Nmap scan report for (.*?) ?(?:\((.*?)\))?")
    port_service_regex = re.compile(r"(\d+)\/(tcp|udp)\s+(open)\s+([a-zA-Z0-9_.-]+)\s*(.*)")

    for line in output_content.splitlines():
        host_match = host_regex.search(line)
        if host_match:
            if current_host_info:
                parsed_data["hosts"].append(current_host_info)
            hostname = host_match.group(1).strip()
            ip_address = host_match.group(2).strip() if host_match.group(2) else hostname
            current_host_info = {"host": hostname, "ip": ip_address, "ports": [], "status": "up"}
            continue
        
        if current_host_info:
            service_match = port_service_regex.match(line.strip())
            if service_match:
                current_host_info["ports"].append({
                    "port": service_match.group(1),
                    "protocol": service_match.group(2),
                    "service": service_match.group(4).strip(),
                    "version": service_match.group(5).strip()
                })

    if current_host_info:
        parsed_data["hosts"].append(current_host_info)
    return parsed_data


def parse_nmap_xml_python_nmap(xml_file_path):
    """
    Parses Nmap XML output using the python-nmap library. This is the preferred method.
    """
    nm = nmap.PortScanner()
    parsed_data = {"hosts": []}
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        if not xml_content.strip():
            return {"hosts": [], "error": "Nmap XML file is empty."}

        scan_result = nm.analyse_nmap_xml_scan(xml_content)
        
        if not nm.all_hosts():
            if nm.scanstats().get('error', '').lower() == 'true':
                 errormsg = nm.scanstats().get('errormsg', 'Unknown Nmap error in XML.')
                 return {"hosts": [], "error": f"Nmap error from XML: {errormsg}"}
            return parsed_data

        for host_ip in nm.all_hosts():
            host_info = nm[host_ip]
            current_host_data = {
                "host": host_info.hostname() or host_ip,
                "ip": host_ip,
                "status": host_info.state(),
                "ports": [],
                "osmatch": [],
                "host_cpes": []
            }

            if 'osmatch' in host_info and host_info['osmatch']:
                for osmatch in host_info['osmatch']:
                    os_details = {"name": osmatch.get('name', 'N/A'), "accuracy": osmatch.get('accuracy', 'N/A'), "cpe": []}
                    if 'osclass' in osmatch:
                        for osclass in osmatch.get('osclass', []):
                            if isinstance(osclass, dict) and 'cpe' in osclass and osclass['cpe']:
                                for cpe_item in osclass['cpe']:
                                    if cpe_item not in os_details["cpe"]: os_details["cpe"].append(cpe_item)
                                    if cpe_item not in current_host_data["host_cpes"]: current_host_data["host_cpes"].append(cpe_item)
                    current_host_data["osmatch"].append(os_details)
            
            for proto in host_info.all_protocols():
                ports_on_proto = host_info[proto].keys()
                for port in ports_on_proto:
                    port_details = host_info[proto][port]
                    if port_details.get('state') == "open":
                        current_host_data["ports"].append({
                            "port": str(port), "protocol": proto, "state": port_details.get('state'),
                            "service": port_details.get('name'), "version": port_details.get('version', ''),
                            "product": port_details.get('product', ''), "extrainfo": port_details.get('extrainfo', ''),
                            "cpe": port_details.get('cpe', '') 
                        })
            parsed_data["hosts"].append(current_host_data)
            
    except FileNotFoundError:
        return {"hosts": [], "error": "Nmap XML file not found"}
    except nmap.PortScannerError as e:
        return {"hosts": [], "error": f"Nmap XML parsing error: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Unexpected error parsing Nmap XML {xml_file_path}: {e}")
        return {"hosts": [], "error": f"An unexpected error occurred: {str(e)}"}
        
    return parsed_data