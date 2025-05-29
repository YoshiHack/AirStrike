# ICMP Flood Attack Framework

This is a web-based ICMP flood attack tool with an AirStrike-inspired interface. The application provides a user-friendly web interface for network scanning and ICMP flood attacks.

> ⚠️ **Warning:** This tool is intended for educational purposes and authorized penetration testing only. Unauthorized use against networks you do not own or have permission to test is illegal and unethical.

## Features

- **Network Scanning**: Discover hosts on your local network using ARP scanning
- **ICMP Flood Attack**: Send a flood of ICMP packets to target systems
- **Real-time Monitoring**: Track attack progress and view logs in real-time
- **Modern UI**: Sleek, responsive interface with dark/light theme support

## Prerequisites

- **Operating System:** Linux (e.g., Kali, Ubuntu)
- **Root Privileges:** Required for network operations
- **Installed Tools:**
  - Python 3.x
  - hping3 (for ICMP flooding)

## Installation

1. **Clone the repository** or download the files

2. **Install required Python packages**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install hping3** (if not already installed)

   ```bash
   sudo apt update
   sudo apt install hping3
   ```

## Usage

1. **Run the application with root privileges**

   ```bash
   sudo python app_new.py
   ```

2. **Access the web interface**

   Open your browser and navigate to: `http://localhost:5000`

3. **Workflow**

   - Start by scanning your network on the Network Scan page
   - Select a target from the scan results
   - Configure and launch an ICMP flood attack
   - Monitor the attack progress and logs in real-time

## Architecture

The application uses:
- Flask for the web server
- Flask-SocketIO for real-time updates
- Scapy for network scanning
- hping3 for ICMP flood attacks

## Disclaimer

Use this tool responsibly. The author is not responsible for any misuse or damage caused by this application. Always ensure you have explicit permission before testing any network or system.
