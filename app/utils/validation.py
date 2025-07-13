# /S2E/app/utils/validation.py
# Security validation utilities for input sanitization

import re
import os
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import ipaddress

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

def sanitize_project_name(name: str) -> str:
    """Sanitize project name to prevent injection attacks."""
    if not name or len(name.strip()) == 0:
        raise ValidationError("Project name cannot be empty")
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name.strip())
    
    if len(sanitized) > 128:
        raise ValidationError("Project name too long (max 128 characters)")
    
    if len(sanitized) < 1:
        raise ValidationError("Project name too short")
    
    return sanitized

def validate_target(target: str) -> bool:
    """Validate target input (IP, domain, or network range)."""
    if not target or len(target.strip()) == 0:
        return False
    
    target = target.strip()
    
    # Check for IP address or CIDR
    try:
        ipaddress.ip_network(target, strict=False)
        return True
    except ValueError:
        pass
    
    # Check for domain name
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if re.match(domain_pattern, target):
        return True
    
    # Check for URL
    try:
        parsed = urlparse(target)
        if parsed.scheme and parsed.netloc:
            return True
    except:
        pass
    
    return False

def sanitize_target_list(targets_string: str) -> List[str]:
    """Sanitize and validate a list of targets."""
    if not targets_string:
        return []
    
    targets = []
    for line in targets_string.strip().split('\n'):
        target = line.strip()
        if target and validate_target(target):
            targets.append(target)
    
    return targets

def validate_tool_id(tool_id: str) -> bool:
    """Validate tool ID against allowed tools."""
    allowed_tools = {'nmap', 'searchsploit', 'sqlmap', 'dirb', 'curl', 'gobuster'}
    return tool_id in allowed_tools

def sanitize_command_options(options: str) -> str:
    """Sanitize command line options to prevent injection."""
    if not options:
        return ""
    
    # Remove potentially dangerous characters and patterns
    dangerous_patterns = [
        r'[;&|`$]',  # Shell operators
        r'\(\)',     # Command substitution
        r'\{.*\}',   # Brace expansion
        r'\[.*\]',   # Character classes
        r'<.*>',     # Redirection
        # Removed backslash check as it's common in Windows paths
    ]
    
    sanitized = options
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized)
    
    return sanitized.strip()

def normalize_path(path: str) -> str:
    """Normalize path for cross-platform compatibility."""
    if not path:
        return ""
    
    import os.path
    
    # Convert to absolute path and normalize
    abs_path = os.path.abspath(path)
    norm_path = os.path.normpath(abs_path)
    
    return norm_path

def validate_file_path(path: str, allowed_dir: str) -> bool:
    """Validate file path to prevent path traversal attacks."""
    if not path:
        return False
    
    try:
        # Normalize paths for cross-platform compatibility
        import os.path
        
        # Convert to absolute paths and normalize
        real_path = os.path.realpath(os.path.abspath(path))
        allowed_real = os.path.realpath(os.path.abspath(allowed_dir))
        
        # Ensure the path is within the allowed directory
        # Use os.path.commonpath for cross-platform compatibility
        try:
            common_path = os.path.commonpath([real_path, allowed_real])
            return common_path == allowed_real
        except ValueError:
            # This can happen on Windows when paths are on different drives
            # In that case, check if the real_path starts with allowed_real
            return real_path.startswith(allowed_real)
            
    except (OSError, ValueError):
        return False

def sanitize_username(username: str) -> str:
    """Sanitize username input."""
    if not username or len(username.strip()) == 0:
        raise ValidationError("Username cannot be empty")
    
    # Only allow alphanumeric characters and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', username.strip())
    
    if len(sanitized) > 64:
        raise ValidationError("Username too long (max 64 characters)")
    
    if len(sanitized) < 1:
        raise ValidationError("Username too short")
    
    return sanitized

def validate_json_structure(data: dict, required_keys: List[str]) -> bool:
    """Validate JSON structure has required keys."""
    return all(key in data for key in required_keys)

def escape_html(text: str) -> str:
    """Escape HTML characters to prevent XSS."""
    if not text:
        return ""
    
    html_escapes = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    }
    
    for char, escape in html_escapes.items():
        text = text.replace(char, escape)
    
    return text

def validate_command_security(command: str) -> bool:
    """Validate command for security issues before execution."""
    if not command:
        return False
    
    import re
    
    # Check for dangerous shell operators and patterns
    dangerous_patterns = [
        (r'[;&|`$]', 'shell operators'),  # Shell operators
        (r'\(\)', 'command substitution'),     # Command substitution
        (r'\{.*\}', 'brace expansion'),   # Brace expansion
        (r'<.*>', 'redirection'),     # Redirection
        # Removed backslash check as it's common in Windows paths
    ]
    
    for pattern, description in dangerous_patterns:
        if re.search(pattern, command):
            print(f"Security warning: Dangerous {description} detected in command")
            return False
    
    # Additional check for command injection attempts
    # Look for patterns that could be used for command injection
    injection_patterns = [
        (r'`.*`', 'backtick command substitution'),           # Backticks for command substitution
        (r'\$\(.*\)', 'dollar command substitution'),       # $() command substitution
        (r'&&.*&&', 'multiple command execution'),         # Multiple command execution
        (r'\|\|.*\|\|', 'multiple command execution'),     # Multiple command execution
        (r';.*;', 'multiple command execution'),           # Multiple command execution
        (r'&.*&', 'background execution'),           # Background execution
    ]
    
    for pattern, description in injection_patterns:
        if re.search(pattern, command):
            print(f"Security warning: Potential {description} detected")
            return False
    
    return True 