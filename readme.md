# Security Toolkit Web Application

A unified web interface for running multiple cybersecurity tools simultaneously, including Nmap, SearchSploit, SQLMap, Dirb, and Curl.

## Features

- Run multiple security tools from a single web interface
- Real-time monitoring of tool execution and output
- Task management system with status tracking
- Output capture and storage for later analysis
- Nmap output parsing and analysis tab
- Follow-up actions: run SearchSploit queries directly from Nmap scan results
- User authentication system (simple, not production-grade)
- Modern Bootstrap-based UI with custom CSS/JS

## Supported Tools

- **Nmap**: Network scanner for discovering hosts and services
- **SearchSploit**: Exploit-DB search tool
- **SQLMap**: Automated SQL injection tool
- **Dirb**: Web content scanner
- **Curl**: HTTP/HTTPS requests (basic)

> **Note:** Metasploit is *not* currently integrated, despite some references in the UI. Only the above tools are supported.

## Prerequisites

- Python 3.8+
- Required security tools installed on your system and available in your PATH:
  - nmap
  - searchsploit
  - sqlmap
  - dirb
  - curl

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd Webapp
```

2. Create a virtual environment (recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Configuration

- The application uses a simple user authentication system. Default credentials:
  - Username: `admin`
  - Password: `securepassword123`

  > **Change these credentials before using in any real environment!**

- Tool configurations can be modified in `app.py` under the `TOOLS` dictionary.

## Usage

1. Start the application:
```bash
python app.py
```

2. Access the web interface at [http://localhost:5000]

3. Log in with your credentials

4. start a new scan with different Intensity

5. Monitor task progress and view results in real-time

6. For Nmap scans, use the "Analysis" tab to view parsed results and run follow-up SearchSploit queries for discovered services/versions.

## Customization

- UI is built with Bootstrap and custom CSS/JS in `static/css/` and `static/js/`.
- HTML templates are in `templates/`.
- You can add or modify tools in the `TOOLS` dictionary in `app.py`.

## Security Considerations

- This tool is for educational and lab use only.
- Always ensure you have proper authorization before scanning any targets.
- Use in controlled, authorized environments only.
- Not recommended for production use without significant security hardening.

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request