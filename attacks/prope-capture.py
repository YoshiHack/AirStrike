#!/usr/bin/env python3

import codecs
from scapy.all import *

def handler(p):
    if not p.haslayer(Dot11ProbeReq):
        return

    rssi = p[RadioTap].dBm_AntSignal if p.haslayer(RadioTap) and hasattr(p[RadioTap], 'dBm_AntSignal') else 'N/A'
    dst_mac = p[Dot11].addr1
    src_mac = p[Dot11].addr2
    ap_mac = src_mac  # In probe request, the source is the client sending it

    ssid = "<not available>"
    try:
        elt = p.getlayer(Dot11Elt)
        while elt:
            if elt.ID == 0:  # SSID element
                ssid_bytes = elt.info
                if ssid_bytes:
                    ssid = ssid_bytes.decode('utf-8', errors='replace')
                else:
                    ssid = "<hidden>"
                break
            elt = elt.payload.getlayer(Dot11Elt)
    except:
        pass

    info = f"rssi={rssi}dBm, dst={dst_mac}, src={src_mac}, ap={ap_mac}, ssid=\"{ssid}\""
    print(f"[ProbReq ] {info}")

if __name__ == "__main__":
    sniff(iface="wlan0", prn=handler, store=0)
