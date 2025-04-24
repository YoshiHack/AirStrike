    _     _        ____   _          _  _
   / \   (_) _ __ / ___| | |_  _ __ (_)| | __  ___ 
  / _ \  | || '__|\___ \ | __|| '__|| || |/ / / _ \
 / ___ \ | || |    ___) || |_ | |   | ||   < |  __/
/_/   \_\|_||_|   |____/  \__||_|   |_||_|\_\ \___|
```

AirStrike is a modular, Python-based WiFi hacking framework developed as a graduation project. It provides powerful tools for:

- **Deauthentication Attacks**: Force clients to disconnect from their access point.
- **WPA/WPA2 Handshake Capture & Cracking**: Capture four-way handshakes and attempt to recover the network password using a wordlist.
- **Evil Twin Attack**: Clone legitimate access points to lure and interact with clients.

> ⚠️ **Warning:** AirStrike is intended for educational and authorized penetration testing only. Unauthorized use against networks you do not own or have permission to test is illegal and unethical.

---

## Features

1. **Deauthentication Attack** (`deauth_attack.py`)
2. **Handshake Capture & Cracker** (`capture_attack.py` + handshake logic in `main.py`)
3. **Evil Twin Attack** (`evil_twin.py`)
4. **MITM Attack** *(Coming Soon)*
5. **DNS Spoofing** *(Coming Soon)*
6. **SSL Stripping** *(Coming Soon)*

---

## Repository Structure

```
├── attacks
│   ├── capture_attack.py      # Worker for capturing WPA handshakes
│   ├── deauth_attack.py       # Worker for performing deauthentication floods
│   ├── evil_twin.py           # Evil Twin attack module
│   ├── mitm.py                # (Planned) Man-in-the-Middle module
│   └── __init__.py
├── utils
│   ├── banner.py              # ASCII art and team banner
│   └── network_utils.py       # Scanning, mode-switching, and AP selection helpers
├── main.py                    # CLI menu and orchestration
├── requirements.txt           # Python package dependencies
└── README.md                  # This documentation
```

---

## Prerequisites

- **Operating System:** Linux (e.g., Kali, Ubuntu) with wireless NIC supporting monitor mode.
- **Root Privileges:** Many operations require `sudo` (monitor mode, channel lock).
- **Installed Tools:**
  - `iwconfig` / `aircrack-ng` suite
  - `tshark` (part of Wireshark CLI)

## Installation

```bash
sudo apt update
sudo apt install -y python3-pip aircrack-ng tshark
pip3 install -r requirements.txt
```

## Usage

```bash
sudo python3 main.py
```

### Main Menu:
```
========================================
AirStrike - Main Menu
========================================
1. Deauth Attack
2. Handshake Cracker
3. Evil Twin Attack
4. MITM Attack (Coming Soon)
5. DNS Spoofing (Coming Soon)
6. SSL Stripping (Coming Soon)
0. Exit
```

---

## Wordlist and Captures

- Default wordlist path: `/usr/share/wordlists/rockyou.txt`
- Captured handshakes are stored under:
  ```
  ./captures/<BSSID-MAC>/capture-01.cap
  ```

---

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or pull request on GitHub.

---

## Disclaimer

Use AirStrike responsibly. Only test on networks you own or have explicit permission to test. The author is not responsible for misuse.
