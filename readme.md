# Security Toolkit Web Application

A unified web interface for running multiple cybersecurity tools simultaneously, including nmap, searchsploit, metasploit, sqlmap, and more.

## Features

- Run multiple security tools simultaneously from a single interface
- Real-time monitoring of tool execution progress
- Task management system with status tracking
- Output capture and storage for later analysis
- Support for popular tools like Nmap, SearchSploit, SQLMap, and Dirb
- User authentication system
- Clean and modern Bootstrap-based UI

## Prerequisites

- Python 3.8+
- Required security tools installed on the system:
  - Nmap
  - SearchSploit
  - SQLMap
  - Dirb

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd webapp
```

2. Create a virtual environment (recommended)
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Configuration

1. The application uses a simple user authentication system. Default credentials:
   - Username: admin
   - Password: securepassword123
   
   Note: In production, please change these credentials and implement proper authentication.

2. Tool configurations can be modified in `app.py` under the `TOOLS` dictionary.

## Usage

1. Start the application:
```bash
python app.py
```

2. Access the web interface at `http://localhost:5000`

3. Log in with your credentials

4. Select a tool and configure the parameters:
   - Nmap: Network scanning
   - SearchSploit: Exploit database search
   - SQLMap: SQL injection testing
   - Dirb: Web content scanning

5. Monitor task progress and view results in real-time

## Security Considerations

- This tool is for educational purposes only
- Always ensure you have proper authorization before scanning any targets
- Use in controlled, authorized environments only
- Not recommended for production use without security hardening

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request