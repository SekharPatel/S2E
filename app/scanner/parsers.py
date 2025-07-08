# /S2E/app/scanner/parsers.py

from flask import current_app
import re
import nmap
import os

def parse_nmap_for_http_hosts(filepath):
    """
    Parses a raw Nmap output file and returns a list of URLs (http/https)
    for hosts with common web ports open.
    """
    if not os.path.exists(filepath):
        return []

    found_hosts = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find IPs or hostnames in "Nmap scan report for ..." lines
    host_regex = re.compile(r"Nmap scan report for ([a-zA-Z0-9\.\-_]+)")
    # Regex to find open web ports
    port_regex = re.compile(r"(\d+)/(tcp|udp)\s+open\s+(http|https|http-proxy)")
    
    current_host = None
    for line in content.splitlines():
        host_match = host_regex.search(line)
        if host_match:
            current_host = host_match.group(1)
            continue
        
        if current_host:
            port_match = port_regex.search(line)
            if port_match:
                port = port_match.group(1)
                service = port_match.group(3)
                protocol = "https" if '443' in port or 'https' in service else "http"
                found_hosts.add(f"{protocol}://{current_host}:{port}")
                
    return list(found_hosts)

def parse_nmap_xml_for_services(xml_file_path):
    """
    Parses an Nmap XML file and returns a structured list of open services.
    This is the core data source for the playbook engine.
    """
    if not os.path.exists(xml_file_path) or os.path.getsize(xml_file_path) == 0:
        return []

    nm = nmap.PortScanner()
    found_services = []
    
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        scan_result = nm.analyse_nmap_xml_scan(xml_content)
        
        for host in nm.all_hosts():
            if 'tcp' in nm[host]:
                for port in nm[host]['tcp']:
                    service_info = nm[host]['tcp'][port]
                    if service_info.get('state') == 'open':
                        protocol = 'https' if '443' in str(port) or 'ssl' in service_info.get('name', '') else 'http'
                        found_services.append({
                            'host': host,
                            'port': str(port),
                            'service_name': service_info.get('name', 'unknown'),
                            'product': service_info.get('product', ''),
                            'version': service_info.get('version', ''),
                            'protocol': protocol # For constructing URLs like http:// or https://
                        })
    except Exception as e:
        print(f"Error parsing Nmap XML file {xml_file_path}: {e}")

    return found_services

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

        # Use analyse_nmap_xml_scan to parse from a string/file content
        scan_result = nm.analyse_nmap_xml_scan(xml_content)
        
        if not nm.all_hosts():
            if nm.scanstats().get('error', '').lower() == 'true':
                 errormsg = nm.scanstats().get('errormsg', 'Unknown Nmap error in XML.')
                 return {"hosts": [], "error": f"Nmap error from XML: {errormsg}"}
            return parsed_data # No hosts found, but no error

        for host_ip in nm.all_hosts():
            host_info = nm[host_ip]
            current_host_data = {
                "host": host_info.hostname() or host_ip,
                "ip": host_ip,
                "status": host_info.state(),
                "ports": [],
                "osmatch": [],
                "host_cpes": [] # Aggregate CPEs for the host
            }

            # Get OS Information
            if 'osmatch' in host_info and host_info['osmatch']:
                for osmatch in host_info['osmatch']:
                    os_details = {"name": osmatch.get('name', 'N/A'), "accuracy": osmatch.get('accuracy', 'N/A'), "cpe": []}
                    if 'osclass' in osmatch:
                        for osclass in osmatch.get('osclass', []):
                            if isinstance(osclass, dict) and 'cpe' in osclass and osclass['cpe']:
                                for cpe_item in osclass['cpe']:
                                    if cpe_item not in os_details["cpe"]: os_details["cpe"].append(cpe_item)
                                    # Also add to the host-level CPE list
                                    if cpe_item not in current_host_data["host_cpes"]: current_host_data["host_cpes"].append(cpe_item)
                    current_host_data["osmatch"].append(os_details)
            
            # Get Port/Service Information
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