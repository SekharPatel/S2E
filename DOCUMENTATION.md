# Scan 2 Exploit (S2E) - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Performance Optimizations](#performance-optimizations)
5. [Getting Started](#getting-started)
6. [User Guide](#user-guide)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [Database Schema](#database-schema)
10. [Troubleshooting](#troubleshooting)
11. [Contributing](#contributing)

---

## Overview

**Scan 2 Exploit (S2E)** is a sophisticated web-based cybersecurity scanning orchestration platform designed to streamline the initial phases of penetration testing. It provides a unified interface for managing multiple scanning tools, organizing projects, and automating follow-up actions based on scan results.

S2E transforms complex command-line security tools into an intuitive web dashboard, making it easier for security professionals to conduct comprehensive assessments while maintaining detailed records of all activities.

### Key Philosophy
- **Simplicity**: One-command setup with minimal dependencies
- **Persistence**: All data survives application restarts
- **Scalability**: Built-in task queue system for handling multiple concurrent scans
- **Security**: Safe execution environment with proper input validation
- **Extensibility**: Configuration-driven tool integration

---

## Features

### 🔐 **Secure Authentication System**
- Database-backed user management with bcrypt password hashing
- Session-based authentication with Flask-Login
- User isolation ensuring project and scan data privacy

### 📊 **Project Management**
- Hierarchical organization: Projects → Targets → Tasks
- Multi-target support with bulk operations
- Project-scoped scanning and reporting
- Persistent project state across sessions

### 🔄 **Persistent Task Queue System**
- **SQLite-based queue** replacing in-memory solutions
- **Restart-safe**: Tasks survive application restarts
- **Priority-based scheduling** for critical scans
- **Automatic recovery** of interrupted tasks
- **Zero additional dependencies** - uses existing SQLAlchemy setup

### 🛠️ **Tool Integration**
- **Nmap**: Network discovery and port scanning with XML parsing
- **SearchSploit**: Exploit database searches
- **Dirb**: Directory brute-forcing
- **Custom Tools**: Easy integration via JSON configuration

### 📋 **Advanced Task Management**
- Real-time status updates (pending, running, completed, failed)
- Live output streaming during task execution
- Task history with searchable records
- Process control (start, stop, monitor)
- Bulk operations across multiple targets

### 🤖 **Playbook Automation**
- Automated scan workflows based on discovered services
- Trigger scans → Service discovery → Follow-up actions
- Configurable rules for automatic exploit searches
- Chain complex scanning scenarios

### 📈 **Rich Reporting**
- **Nmap XML parsing** with structured service detection
- **CVE identification** through service version analysis
- **Export capabilities** for external reporting tools
- **Historical analysis** of scan results

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (Flask)                    │
├─────────────────────────────────────────────────────────────┤
│                  Authentication Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Projects  │  Scanner  │  Tasks  │  Auth  │  Home          │
│  Module    │  Module   │ Module  │ Module │ Module         │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  Projects   │ │   Tasks     │ │  JobQueue   │          │
│  │             │ │             │ │ (New!)      │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                 Task Manager (Background)                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Persistent Queue Worker                                ││
│  │  • Polls SQLite database for new jobs                  ││
│  │  • Executes tasks safely in subprocess                 ││
│  │  • Handles task recovery after restart                 ││
│  │  • Manages playbook automation                         ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    File System                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Config    │ │   Output    │ │  Instance   │          │
│  │   Files     │ │   Files     │ │   Data      │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **User Authentication**: Login verification and session management
2. **Project Selection**: Set active project context
3. **Target Definition**: Specify scan targets (IPs, domains, ranges)
4. **Task Creation**: Configure tools and parameters
5. **Queue Management**: Tasks added to persistent SQLite queue
6. **Background Processing**: Worker thread processes tasks sequentially
7. **Result Storage**: Output files and metadata stored in database
8. **Real-time Updates**: WebSocket-like polling for live status updates

---

## Performance Optimizations

### 🚀 **Persistent Queue System**

**Problem Solved**: The original in-memory queue system lost all pending tasks when the application restarted, causing frustration and lost work.

**Solution**: Implemented a SQLite-based persistent queue with the following benefits:

#### **Database-Backed Queue**
- **JobQueue Table**: Stores all pending, processing, and completed jobs
- **Priority System**: Higher priority jobs (e.g., playbooks) execute first
- **Status Tracking**: Comprehensive job lifecycle management
- **Automatic Recovery**: Stuck jobs are automatically reset on startup

#### **Implementation Details**
```python
class JobQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(64), nullable=False)  # 'single_task' or 'playbook'
    job_data = db.Column(db.Text, nullable=False)        # JSON-encoded parameters
    status = db.Column(db.String(32), default='pending') # 'pending', 'processing', 'completed', 'failed'
    priority = db.Column(db.Integer, default=0)          # Higher = more important
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
```

#### **Benefits**
- **Zero New Dependencies**: Uses existing SQLAlchemy + SQLite setup
- **Restart Safety**: All queued jobs survive application restarts
- **Simplicity**: Same user experience (`git clone`, `pip install`, `python run.py`)
- **Reliability**: Database ACID properties ensure data integrity
- **Monitoring**: Full audit trail of all job executions

#### **Performance Metrics**
- **Queue Operations**: O(log n) complexity with database indexes
- **Memory Usage**: Constant memory footprint regardless of queue size
- **Scalability**: Can handle thousands of queued jobs without performance degradation
- **Recovery Time**: Sub-second recovery of interrupted jobs on restart

---

## Getting Started

### Prerequisites

- **Python 3.10+** with pip
- **Git** for repository cloning
- **Security Tools**:
  - [Nmap](https://nmap.org/download.html) - Network mapping
  - [SearchSploit](https://www.exploit-db.com/searchsploit) - Exploit database
  - [Dirb](http://dirb.sourceforge.net/) - Directory brute-forcing

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/SekharPatel/S2E.git
cd S2E
```

2. **Set Up Python Environment**
```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Initialize Database**
```bash
export FLASK_APP=run.py

# Initialize migration system
flask db init

# Create database tables
flask db migrate -m "Initial migration"
flask db upgrade
```

4. **Create Admin User**
```bash
flask create-user admin your-secure-password
```

5. **Launch Application**
```bash
python run.py
```

Navigate to `http://localhost:5000` and log in with your credentials.

### Quick Start Checklist

- [ ] Security tools installed and in PATH
- [ ] Database initialized successfully
- [ ] Admin user created
- [ ] Application launches without errors
- [ ] Login successful
- [ ] First project created
- [ ] First scan executed

---

## User Guide

### 📁 **Project Management**

#### Creating Projects
1. Click "New Project" from the dashboard
2. Provide project name and description
3. Define initial targets (IP addresses, domains, CIDR ranges)
4. Submit to create and automatically set as active project

#### Managing Targets
- **Add Targets**: One per line in the target textarea
- **Supported Formats**:
  - Single IPs: `192.168.1.1`
  - Domains: `example.com`
  - CIDR ranges: `192.168.1.0/24`
  - Port specifications: `192.168.1.1:80,443`

#### Project Operations
- **Edit**: Modify project details and targets
- **Delete**: Remove project and all associated data
- **Switch**: Change active project context

### 🎯 **Scanning Operations**

#### Single Target Scans
1. Select tool from dropdown (Nmap, SearchSploit, Dirb)
2. Enter target specification
3. Configure tool options
4. Execute scan

#### Bulk Project Scans
1. Ensure targets are defined in active project
2. Select scanning tool
3. Configure options (applied to all targets)
4. Execute project-wide scan

#### Playbook Automation
1. Navigate to Playbooks section
2. Select appropriate playbook for your scenario
3. Execute playbook against active project
4. Monitor automated task execution

### 📊 **Task Monitoring**

#### Real-time Updates
- **Status Indicators**: Color-coded task status
- **Progress Monitoring**: Live output streaming
- **Process Control**: Stop running tasks if needed

#### Task History
- **Search**: Find specific tasks by tool, target, or date
- **Filter**: View tasks by status or project
- **Export**: Download task results for external analysis

### 🔍 **Results Analysis**

#### Nmap Results
- **Service Detection**: Parsed service information
- **Version Analysis**: Software versions identified
- **Vulnerability Hints**: Potential security issues
- **Export Options**: XML, JSON, and text formats

#### Follow-up Actions
- **Exploit Search**: Automatic SearchSploit queries
- **Service Enumeration**: Targeted service scans
- **Custom Actions**: User-defined follow-up procedures

---

## Configuration

### 📝 **Tool Configuration** (`config/tools.json`)

```json
{
  "TOOLS": {
    "nmap": {
      "name": "Nmap",
      "description": "Network mapper for host discovery and port scanning",
      "command": "nmap {options} {target}",
      "default_options": "-sS -sV -O --script=vuln",
      "output_parsers": ["xml", "text"]
    },
    "searchsploit": {
      "name": "SearchSploit",
      "description": "Exploit database search",
      "command": "searchsploit {options} {query}",
      "default_options": "--colour --overflow --json",
      "output_parsers": ["json"]
    }
  }
}
```

### 🤖 **Playbook Configuration** (`config/playbooks.json`)

```json
{
  "PLAYBOOKS": [
    {
      "id": "basic_recon",
      "name": "Basic Reconnaissance",
      "description": "Standard network discovery and service enumeration",
      "trigger": {
        "tool_id": "nmap",
        "options": "-sS -sV -A"
      },
      "rules": [
        {
          "on_service": ["http", "https"],
          "action": {
            "tool_id": "dirb",
            "name": "Directory Brute Force",
            "options": "http://{host}:{port}/"
          }
        },
        {
          "on_service": ["ssh"],
          "action": {
            "tool_id": "searchsploit",
            "name": "SSH Exploit Search",
            "options": "ssh {service_version}"
          }
        }
      ]
    }
  ]
}
```

### 🔧 **Application Configuration**

#### Environment Variables
```bash
# Security
export SECRET_KEY="your-secret-key-here"

# Database
export DATABASE_URL="sqlite:///instance/app.db"

# Paths
export OUTPUT_DIR="/path/to/scan/outputs"
export CONFIG_DIR="/path/to/config/files"
```

#### Flask Configuration
```python
# app/__init__.py
app.config.update({
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///instance/app.db',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key'),
    'OUTPUT_DIR': os.path.abspath('output'),
    'CONFIG_DIR': os.path.abspath('config')
})
```

---

## API Reference

### Authentication Endpoints

#### `POST /auth/login`
Authenticate user and create session.

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "admin"
  }
}
```

### Project Management Endpoints

#### `POST /api/projects`
Create new project with targets.

**Request Body:**
```json
{
  "name": "Web Application Test",
  "description": "Testing web application security",
  "targets": "192.168.1.100\n192.168.1.101\nexample.com"
}
```

#### `GET /api/projects/<int:project_id>`
Retrieve project details including targets.

**Response:**
```json
{
  "id": 1,
  "name": "Web Application Test",
  "description": "Testing web application security",
  "targets": "192.168.1.100\n192.168.1.101\nexample.com",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Task Management Endpoints

#### `POST /api/scanner/run`
Execute single scan task.

**Request Body:**
```json
{
  "tool_id": "nmap",
  "target": "192.168.1.100",
  "options": "-sS -sV -A"
}
```

#### `GET /api/task/<int:task_id>/status`
Get real-time task status.

**Response:**
```json
{
  "status": "running",
  "progress": 45,
  "pid": 12345,
  "start_time": "2024-01-15T10:30:00Z"
}
```

#### `GET /api/task/<int:task_id>/output`
Stream task output in real-time.

**Response:**
```json
{
  "status": "success",
  "output": "Starting Nmap scan...\n192.168.1.100 is up (0.001s latency)\n..."
}
```

### Queue Management Endpoints

#### `GET /api/queue/status`
Get current queue status and statistics.

**Response:**
```json
{
  "pending_jobs": 5,
  "processing_jobs": 1,
  "completed_jobs": 23,
  "failed_jobs": 2,
  "total_jobs": 31,
  "queue_health": "healthy"
}
```

---

## Database Schema

### Core Tables

#### `user` - User Authentication
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL
);
```

#### `project` - Project Management
```sql
CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

#### `target` - Target Specifications
```sql
CREATE TABLE target (
    id INTEGER PRIMARY KEY,
    value VARCHAR(512) NOT NULL,
    project_id INTEGER NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(id)
);
```

#### `task` - Task Execution Records
```sql
CREATE TABLE task (
    id INTEGER PRIMARY KEY,
    tool_id VARCHAR(64) NOT NULL,
    command VARCHAR(1024) NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(64) DEFAULT 'starting',
    pid INTEGER,
    original_target VARCHAR(256),
    raw_output_file VARCHAR(512),
    xml_output_file VARCHAR(512),
    project_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES project(id)
);
```

#### `job_queue` - Persistent Task Queue ⭐
```sql
CREATE TABLE job_queue (
    id INTEGER PRIMARY KEY,
    job_type VARCHAR(64) NOT NULL,
    job_data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    status VARCHAR(32) DEFAULT 'pending',
    priority INTEGER DEFAULT 0
);
```

### Relationships

```
user (1) ──────────── (many) project
project (1) ─────────── (many) target
project (1) ─────────── (many) task
job_queue (independent) ─────── references task via JSON
```

### Indexes

- `user.username` - Unique index for fast login
- `task.start_time` - Index for chronological sorting
- `task.status` - Index for status filtering
- `job_queue.status` - Index for queue processing
- `job_queue.priority` - Index for priority ordering
- `job_queue.created_at` - Index for FIFO ordering

---

## Troubleshooting

### Common Issues

#### Database Connection Errors
**Problem**: `sqlite3.OperationalError: database is locked`
**Solution**: 
```bash
# Kill any running instances
pkill -f "python run.py"

# Remove lock file if exists
rm instance/app.db-journal

# Restart application
python run.py
```

#### Missing Dependencies
**Problem**: `ModuleNotFoundError: No module named 'flask'`
**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### Tool Not Found Errors
**Problem**: `FileNotFoundError: [Errno 2] No such file or directory: 'nmap'`
**Solution**:
```bash
# Install required tools
sudo apt-get install nmap
sudo apt-get install dirb

# Verify installation
which nmap
which dirb
```

#### Queue System Issues
**Problem**: Tasks stuck in "processing" state
**Solution**:
```bash
# The system automatically recovers stuck jobs on restart
python run.py
```

#### Performance Issues
**Problem**: Slow task execution or high memory usage
**Solution**:
```bash
# Check disk space
df -h

# Monitor system resources
top -p $(pgrep -f "python run.py")

# Clear old output files
find output/ -name "*.txt" -mtime +30 -delete
```

### Debug Mode

Enable debug mode for detailed error messages:
```python
# run.py
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Log Analysis

Monitor application logs:
```bash
# View real-time logs
tail -f instance/app.log

# Search for specific errors
grep -i "error" instance/app.log

# Monitor task manager
grep -i "task manager" instance/app.log
```

---

## Contributing

### Development Setup

1. **Fork Repository**
2. **Create Feature Branch**
```bash
git checkout -b feature/amazing-feature
```

3. **Install Development Dependencies**
```bash
pip install -r requirements-dev.txt
```

4. **Run Tests**
```bash
pytest tests/
```

5. **Code Style**
```bash
# Format code
black app/
flake8 app/
```

### Code Structure

- `app/` - Main application package
  - `__init__.py` - Flask application factory
  - `models.py` - Database models
  - `auth/` - Authentication module
  - `projects/` - Project management
  - `scanner/` - Tool integration
  - `tasks/` - Task management and queue
  - `static/` - CSS, JavaScript, images
  - `templates/` - HTML templates

### Adding New Tools

1. **Update `config/tools.json`**
```json
{
  "your_tool": {
    "name": "Your Tool Name",
    "description": "What your tool does",
    "command": "your-tool {options} {target}",
    "default_options": "--default-flags"
  }
}
```

2. **Create Output Parser** (if needed)
```python
# app/scanner/parsers.py
def parse_your_tool_output(output_file):
    # Parse tool output
    return structured_data
```

3. **Update Templates** (if needed)
```html
<!-- app/templates/scanner.html -->
<option value="your_tool">Your Tool Name</option>
```

### Testing

Run comprehensive tests:
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Coverage report
pytest --cov=app tests/
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/SekharPatel/S2E/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SekharPatel/S2E/discussions)
- **Documentation**: This file and inline code comments

---

*Last updated: January 2024*