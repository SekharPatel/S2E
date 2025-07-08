# Scan 2 Exploit (S2E)

A web-based interface for orchestrating and managing cybersecurity scanning tools. S2E provides a clean dashboard to streamline the initial phases of a penetration test, from network scanning to vulnerability analysis, by wrapping popular command-line tools in a persistent and user-friendly environment.

## Features

-   **Secure User Authentication**: Protected by a database-backed login system with hashed passwords.
-   **Persistent Task History**: All tasks are saved to a local SQLite database, so your scan history survives application restarts.
-   **Dynamic Task Dashboard**: View all tasks in a central location with live status updates (`running`, `completed`, `failed`) without needing to refresh the page.
-   **Configuration-Driven Toolset**: Easily add or modify tools like Nmap, SearchSploit, Dirb, etc., by editing simple JSON configuration files.
-   **Safe Background Execution**: Scans run in background threads, are isolated from the web server process, and are executed safely without shell command injection risks.
-   **Rich Nmap Parsing**: Automatically parses Nmap's XML output to provide a structured view of open ports, services, versions, and CPEs.
-   **Follow-up Actions**: Chain commands together by launching new scans (e.g., SearchSploit) based on the results of a previous Nmap scan.

## Technology Stack

-   **Backend**: Python 3, Flask
-   **Database**: SQLite (via Flask-SQLAlchemy & Flask-Migrate)
-   **Frontend**: HTML5, CSS3, Vanilla JavaScript
-   **Key Python Libraries**: `psutil`, `python-nmap`

## Project Structure

```
S2E/
├── app/
│   ├── __init__.py   # Flask app factory and configuration
|   ├── models.py     # Database models (User, Project, Task, Scan)
│   ├── auth/         # Authentication (login, logout)
│   ├── home/         # Home and landing pages
|   ├── project/      # Project management UI and API
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

## Getting Started: Local Setup

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### 1. Prerequisites

First, ensure you have the necessary system-level dependencies installed.

-   **Python 3.10+** and **pip**
-   **Git** for cloning the repository.
-   **The actual command-line tools** that S2E orchestrates. At a minimum, you need:
    -   [**Nmap**](https://nmap.org/download.html)
    -   [**SearchSploit**](https://www.exploit-db.com/searchsploit) (comes with Kali Linux or can be installed separately)

### 2. Clone the Repository

```bash
git clone https://github.com/SekharPatel/S2E.git
cd S2E
```

### 3. Set Up the Python Environment

It is highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages.

```bash
pip install -r requirements.txt
```

### 5. Set Up the Database

This project uses Flask-Migrate to manage the database schema. The following commands will create the `app.db` file and set up the necessary tables.

```bash
# Set the Flask application entry point for the terminal
# On Windows:
set FLASK_APP=run.py
# On macOS/Linux:
export FLASK_APP=run.py

# 1. Initialize the migration folder (only run this once ever for the project)
flask db init

# 2. Generate the first migration script based on the models
flask db migrate -m "Initialize migration."

# 3. Apply the migration to create the database and its tables
flask db upgrade
```
After these commands, you will see a new `app.db` file in the root `S2E/` directory.

### 6. Create Your First User

Use the built-in CLI command to create your login credentials.

```bash
# Usage: flask create-user <username> <password>
flask create-user admin yoursecurepassword123
```

### 7. Run the Application

You are now ready to start the Flask development server.

```bash
python run.py
```

Open your web browser and navigate to **http://127.0.0.1:5000**. You should see the login page. Log in with the credentials you created in the previous step.

## Configuration

You can easily customize the tools available in S2E by editing the JSON files in the `S2E/config/` directory:
-   `tools.json`: Define the command structure for each tool.
-   `playbook.json`: Define the sequence of tasks and how they interact.
-   `follow-up.json`: Define the actions available in the Nmap analysis tab