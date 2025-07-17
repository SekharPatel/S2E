# Scan 2 Exploit (S2E)

A sophisticated web-based cybersecurity scanning orchestration platform designed to streamline the initial phases of penetration testing. S2E provides a unified interface for managing multiple scanning tools, organizing projects, and automating follow-up actions based on scan results.

S2E transforms complex command-line security tools into an intuitive web dashboard, making it easier for security professionals to conduct comprehensive assessments while maintaining detailed records of all activities.

## Table of Contents
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started: Local Setup](#getting-started-local-setup)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone the Repository](#2-clone-the-repository)
  - [3. Set Up the Python Environment](#3-set-up-the-python-environment)
  - [4. Install Dependencies](#4-install-dependencies)
  - [5. Initialize the Application](#5-initialize-the-application)
  - [6. Run the Application](#6-run-the-application)
- [Quick Start Checklist](#quick-start-checklist)
- [License](#license)
- [Support](#support)


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

## Technology Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (via Flask-SQLAlchemy & Flask-Migrate)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Key Python Libraries**: `psutil`, `python-nmap`
- **Task Queue**: SQLite-based persistent queue system

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (Flask)                    │
├─────────────────────────────────────────────────────────────┤
│                  Authentication Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Projects  │  Scanner  │  Tasks  │  Auth  │  Home           │
│  Module    │  Module   │ Module  │ Module │ Module          │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Projects   │ │   Tasks     │ │  JobQueue   │            │
│  │             │ │             │ │ (New!)      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│                 Task Manager (Background)                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Persistent Queue Worker                                ││
│  │  • Polls SQLite database for new jobs                   ││
│  │  • Executes tasks safely in subprocess                  ││
│  │  • Handles task recovery after restart                  ││
│  │  • Manages playbook automation                          ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    File System                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Config    │ │   Output    │ │  Instance   │            │
│  │   Files     │ │   Files     │ │   Data      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
S2E/
├── app/
│   ├── __init__.py   # Flask app factory and configuration
│   ├── models.py     # Database models (User, Project, Task, JobQueue)
│   ├── auth/         # Authentication (login, logout)
│   ├── home/         # Home and landing pages
│   ├── projects/     # Project management UI and API
│   ├── scanner/      # Logic for running and parsing scans
│   ├── static/       # CSS, JS, Images
│   ├── tasks/        # Task management UI and API
│   └── templates/    # HTML templates
│
├── config/           # JSON-based tool and app configuration
├── migrations/       # Database migration scripts
├── instance/         # Instance-specific config (auto-generated)
├── output/           # Raw and XML output from tool scans
│
├── app.db            # SQLite database file (auto-generated)
├── requirements.txt  # Python dependencies
└── run.py            # Application entry point
```

---

## Getting Started: Local Setup

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### 1. Prerequisites

S2E is recommended to run on **Kali Linux** for the best out-of-the-box experience, but you can also use Windows or other operating systems as long as you install the required tools.

First, ensure you have the following system-level dependencies installed:

-   **Python 3.10+** and **pip**
-   **Git** for cloning the repository
-   **Command-line security tools** that S2E orchestrates. At a minimum, you need:
    -   [**Nmap**](https://nmap.org/download.html)

### 2. Clone the Repository

```bash
git clone https://github.com/SekharPatel/S2E.git
cd S2E
```

### 3. Set Up the Python Environment

It is highly recommended to use a virtual environment to isolate project dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 5. Initialize the Application

This is the most important step. Use the Flask CLI command to set up the database, create an initial user, and seed the application with pre-configured playbooks.

```bash
# Activate your virtual environment first

# Set the Flask application entry point
# On Windows:
set FLASK_APP=run.py
# On macOS/Linux:
export FLASK_APP=run.py

# Run the database initialization command
flask init-db
```

This will:
- Create the database and all tables
- Prompt you for username and password (if not provided)
- Create the initial admin user
- Seed the database with default playbooks

#### Database Initialization Options

You can also provide credentials as command-line arguments:

```bash
# With command-line arguments
flask init-db --username admin --password secure_password

# Or with short flags
flask init-db -u admin -p secure_password

# Force recreation of existing database
flask init-db --force --username admin --password secure_password

# Skip playbook seeding (only create user)
flask init-db --skip-playbooks --username admin --password secure_password
```

#### Available Options

- `--username, -u`: Username for the initial admin user
- `--password, -p`: Password for the initial admin user  
- `--force, -f`: Force recreation of database even if it exists
- `--skip-playbooks`: Skip seeding playbooks (only create user)

If no credentials are provided, the script will prompt for them interactively.

### 6. Run the Application

You are now ready to start the Flask development server.

```bash
flask run
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

## Support

- **Issues**: [GitHub Issues](https://github.com/SekharPatel/S2E/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SekharPatel/S2E/discussions)
- **Documentation**: This comprehensive README