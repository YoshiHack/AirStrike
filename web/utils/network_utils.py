import subprocess
import re
import sys
import os
import time

# Import the shared module for sudo functionality
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from web.shared import run_with_sudo, config, logger

def set_monitor_mode(interface_name):
    """
    Set the wireless interface to monitor mode.
    
    Args:
        interface_name (str): Name of the wireless interface
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use our sudo function instead of direct subprocess calls
        success1, out1, err1 = run_with_sudo(f"ifconfig {interface_name} down")
        success2, out2, err2 = run_with_sudo(f"iwconfig {interface_name} mode monitor")
        success3, out3, err3 = run_with_sudo(f"ifconfig {interface_name} up")
        
        if success1 and success2 and success3:
            logger.info(f"Interface {interface_name} set to monitor mode")
            return True
        else:
            # Log the errors
            if not success1:
                logger.error(f"Failed to bring interface down: {err1}")
            if not success2:
                logger.error(f"Failed to set monitor mode: {err2}")
            if not success3:
                logger.error(f"Failed to bring interface up: {err3}")
                
            # If we need sudo authentication, return False to trigger the auth flow
            if "incorrect password" in (err1 + err2 + err3).lower() or "sudo" in (err1 + err2 + err3).lower():
                config['sudo_configured'] = False
                
            return False
    except Exception as e:
        logger.error(f"Error setting {interface_name} to monitor mode: {str(e)}")
        return False


def set_managed_mode(interface_name):
    """
    Set the wireless interface to managed mode.
    
    Args:
        interface_name (str): Name of the wireless interface
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use our sudo function instead of direct subprocess calls
        success1, out1, err1 = run_with_sudo(f"ifconfig {interface_name} down")
        success2, out2, err2 = run_with_sudo(f"iwconfig {interface_name} mode managed")
        success3, out3, err3 = run_with_sudo(f"ifconfig {interface_name} up")
        
        if success1 and success2 and success3:
            logger.info(f"Interface {interface_name} set to managed mode")
            return True
        else:
            # Log the errors
            if not success1:
                logger.error(f"Failed to bring interface down: {err1}")
            if not success2:
                logger.error(f"Failed to set managed mode: {err2}")
            if not success3:
                logger.error(f"Failed to bring interface up: {err3}")
                
            # If we need sudo authentication, return False to trigger the auth flow
            if "incorrect password" in (err1 + err2 + err3).lower() or "sudo" in (err1 + err2 + err3).lower():
                config['sudo_configured'] = False
                
            return False
    except Exception as e:
        logger.error(f"Error setting {interface_name} to managed mode: {str(e)}")
        return False

def run_scan(interface):
    """
    Scans for available Wi-Fi networks and returns a list of dictionaries
    containing network information.

    Args:
        interface (str): The network interface to use for scanning (e.g., "wlan0").

    Returns:
        list: A list of dictionaries, where each dictionary represents a Wi-Fi network
              and contains its details. Returns an empty list if an error occurs or
              no networks are found.
    """
    logger.info(f"Scanning for Wi-Fi networks on interface {interface}...")
    try:
        # First, make sure the interface is in managed mode and not busy
        # This helps resolve "Device or resource busy" errors
        try:
            # Bring down the interface
            run_with_sudo(f"ifconfig {interface} down")
            # Wait a moment for the interface to settle
            time.sleep(1)
            # Set to managed mode
            run_with_sudo(f"iwconfig {interface} mode managed")
            # Bring it back up
            run_with_sudo(f"ifconfig {interface} up")
            # Wait again for the interface to initialize
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Error resetting interface before scan: {e}")
            # Continue anyway, the scan might still work
        
        # Using iw scan is often preferred over iwlist nowadays if available
        # Trying iwlist first as it was in the original code
        success = False
        output = ""
        error = ""
        
        # Try iwlist first
        success, output, error = run_with_sudo(f"iwlist {interface} scanning")
        
        # If iwlist fails, try iw
        if not success or "Device or resource busy" in error:
            logger.warning(f"iwlist failed: {error}")
            logger.info(f"Trying 'iw dev {interface} scan' as fallback...")
            
            # If we got "Device or resource busy", try to reset the interface
            if "Device or resource busy" in error:
                try:
                    # More aggressive reset
                    run_with_sudo(f"ip link set {interface} down")
                    time.sleep(1)
                    run_with_sudo(f"ip link set {interface} up")
                    time.sleep(2)
                except Exception as reset_err:
                    logger.warning(f"Error during interface reset: {reset_err}")
            
            # Now try with iw
            success, output, error = run_with_sudo(f"iw dev {interface} scan")
            
            if not success:
                logger.error(f"Error running scan command with iw: {error}")
                
                # Check if this is a sudo authentication issue
                if "incorrect password" in error.lower() or "sudo" in error.lower():
                    config['sudo_configured'] = False
                    return []
                
                # If it's still busy, try one more approach with airmon-ng
                if "Device or resource busy" in error:
                    logger.info("Trying airmon-ng to check/kill processes using the interface...")
                    try:
                        # Check if airmon-ng is available
                        check_success, check_out, check_err = run_with_sudo("which airmon-ng")
                        if check_success:
                            # Kill processes that might be using the interface
                            run_with_sudo(f"airmon-ng check kill")
                            time.sleep(2)
                            # Try scan again
                            success, output, error = run_with_sudo(f"iw dev {interface} scan")
                            if not success:
                                logger.error(f"Still failed after airmon-ng: {error}")
                                return []
                        else:
                            logger.warning("airmon-ng not available for advanced interface reset")
                            return []
                    except Exception as airmon_err:
                        logger.error(f"Error using airmon-ng: {airmon_err}")
                        return []
                else:
                    return []

        aps = []
        
        # Debug the output to see what we're working with
        logger.debug(f"Command output first 100 chars: {output[:100]}")
        
        # Check if this is iwlist output
        if success and "Cell" in output:
            logger.info("Parsing iwlist output format")
            current_ap = {}
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('Cell'):
                    if current_ap:  # Save the previous AP before starting a new one
                        # Basic check for essential info before adding
                        if 'BSSID' in current_ap and 'ESSID' in current_ap and 'Channel' in current_ap:
                            aps.append(current_ap)
                        else:
                            logger.debug(f"Skipping incomplete AP: {current_ap}")
                    current_ap = {}
                    match = re.search(r'Address:\s*([\da-fA-F:]+)', line, re.IGNORECASE)
                    if match:
                        current_ap['BSSID'] = match.group(1).upper() # Standardize BSSID case
                elif 'ESSID:' in line:
                    essid_match = re.search(r'ESSID:"(.*?)"', line)
                    if essid_match:
                        current_ap['ESSID'] = essid_match.group(1)
                elif 'Channel:' in line:
                    # Handle potential extra text like "(secondary)"
                    channel_match = re.search(r'Channel:(\d+)', line)
                    if channel_match:
                        current_ap['Channel'] = channel_match.group(1)
                # Add other fields if needed (like Quality, Signal Strength etc.)

            if current_ap: # Add the last AP found
                 if 'BSSID' in current_ap and 'ESSID' in current_ap and 'Channel' in current_ap:
                    aps.append(current_ap)
                 else:
                    logger.debug(f"Skipping last incomplete AP: {current_ap}")

        # Check if this is iw output
        elif success and "BSS " in output:
            logger.info("Parsing iw output format")
            blocks = output.split('BSS ') # Split output by AP blocks
            for block in blocks[1:]: # Skip the first part before the first BSS
                lines = block.strip().split('\n')
                current_ap = {}
                
                # Parse BSSID from first line (format: "BSS 00:11:22:33:44:55(on wlan0)")
                bssid_match = re.search(r'([\da-fA-F:]+)', lines[0])
                if bssid_match:
                    current_ap['BSSID'] = bssid_match.group(1).upper()

                for line in lines[1:]:
                    line = line.strip()
                    if 'SSID: ' in line:
                        current_ap['ESSID'] = line.split('SSID: ', 1)[1].strip()
                    elif 'DS Parameter set: channel' in line:
                        current_ap['Channel'] = line.split('channel', 1)[1].strip()
                    elif 'freq: ' in line: # Alternative way to find channel for some outputs
                         if 'Channel' not in current_ap:
                             try:
                                 freq_match = re.search(r'freq: (\d+)', line)
                                 if freq_match:
                                     freq = int(freq_match.group(1))
                                     if 2412 <= freq <= 2484: # 2.4 GHz band
                                         channel = str(int((freq - 2407) / 5))
                                         current_ap['Channel'] = channel
                                     elif 5180 <= freq <= 5825: # 5 GHz band (approximate mapping)
                                         channel = str(int((freq - 5000) / 5))
                                         current_ap['Channel'] = channel
                             except Exception as e:
                                 logger.debug(f"Error parsing frequency: {e}")

                # Basic check for essential info before adding
                if 'BSSID' in current_ap and current_ap.get('ESSID') and 'Channel' in current_ap:
                     aps.append(current_ap)
                else:
                     logger.debug(f"Skipping incomplete AP from iw: {current_ap}")
        
        # Try generic parsing if the specific formats weren't detected
        elif success:
            logger.info("Using generic parsing for unrecognized output format")
            
            # Look for MAC addresses that might be BSSIDs
            bssid_matches = re.findall(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', output)
            
            # Look for ESSID patterns
            essid_matches = re.findall(r'ESSID:"(.*?)"', output)
            if not essid_matches:
                essid_matches = re.findall(r'SSID: (.*?)$', output, re.MULTILINE)
            
            # Look for channel patterns
            channel_matches = re.findall(r'Channel[:\s]+(\d+)', output, re.IGNORECASE)
            if not channel_matches:
                channel_matches = re.findall(r'channel[:\s]+(\d+)', output, re.IGNORECASE)
            
            # If we found at least one of each, try to create networks
            if bssid_matches:
                # Use the first channel for all if we don't have enough
                default_channel = "1" if not channel_matches else channel_matches[0]
                
                for i, bssid in enumerate(bssid_matches):
                    ap = {'BSSID': bssid.upper()}
                    
                    # Add ESSID if available
                    if i < len(essid_matches):
                        ap['ESSID'] = essid_matches[i]
                    else:
                        ap['ESSID'] = f"Unknown Network {i+1}"
                    
                    # Add channel if available
                    if i < len(channel_matches):
                        ap['Channel'] = channel_matches[i]
                    else:
                        ap['Channel'] = default_channel
                    
                    aps.append(ap)

        if not aps:
             logger.warning("No Wi-Fi networks found or parsed.")
             # Log a small portion of the output to help diagnose parsing issues
             if output:
                 logger.debug(f"Output sample (first 500 chars): {output[:500]}")
        else:
             logger.info(f"Found {len(aps)} Wi-Fi networks.")
        
        return aps

    except Exception as e:
        logger.error(f"An unexpected error occurred during scanning: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def display_and_choose_ap(ap_list):
    """
    Displays a numbered list of APs and prompts the user to choose one.

    Args:
        ap_list (list): A list of AP dictionaries from run_scan.

    Returns:
        tuple: A tuple containing the BSSID and Channel of the chosen AP
               (bssid, channel), or (None, None) if no AP is chosen or
               an error occurs.
    """
    if not ap_list:
        print("No APs available to choose from.")
        return None, None

    print("\nAvailable Access Points:")
    print("-" * 30)
    for i, ap in enumerate(ap_list):
        # Ensure essential keys exist, provide defaults if not
        essid = ap.get('ESSID', 'N/A')
        bssid = ap.get('BSSID', 'N/A')
        channel = ap.get('Channel', 'N/A')
        print(f"{i + 1}. ESSID: {essid:<20} BSSID: {bssid}  Channel: {channel}")
    print("-" * 30)

    while True:
        try:
            choice = input(f"Enter the number of the AP you want to select (1-{len(ap_list)}), or 'q' to quit: ")
            if choice.lower() == 'q':
                print("Selection cancelled.")
                return None, None

            choice_index = int(choice) - 1

            if 0 <= choice_index < len(ap_list):
                selected_ap = ap_list[choice_index]
                selected_bssid = selected_ap.get('BSSID')
                selected_channel = selected_ap.get('Channel')

                if selected_bssid and selected_channel:
                    # Print confirmation of selection, but not the final result later
                    print(f"\nYou selected: {selected_ap.get('ESSID', 'N/A')} ({selected_bssid}) on channel {selected_channel}")
                    return selected_bssid, selected_channel
                else:
                    print("Error: Selected AP data is incomplete (missing BSSID or Channel). Please try again.")
                    return None, None

            else:
                print("Invalid choice. Please enter a number from the list.")

        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
             print("\nSelection cancelled by user.")
             return None, None

# --- Main Execution ---
if __name__ == "__main__":
    # --- Configuration ---
    # !!!!! IMPORTANT: Replace "wlan0" with your actual wireless interface name !!!!!
    wireless_interface = "wlan0"
    # --- End Configuration ---

    # 1. Scan for Networks
    #banner("AirStrike")

    available_aps = run_scan(wireless_interface)
    print(available_aps)

    # 2. Let the user choose
    chosen_bssid = None
    chosen_channel = None
    if available_aps: # Proceed only if scanning was successful and found APs
        chosen_bssid, chosen_channel = display_and_choose_ap(available_aps)

    # 3. Use the chosen information (variables are available but not printed here)
    if chosen_bssid and chosen_channel:
        # --- Removed final print statements ---
        # print("\n--- Selected AP Info ---")
        # print(f"BSSID:   {chosen_bssid}")
        # print(f"Channel: {chosen_channel}")
        # print("------------------------")

        # You can now use the variables 'chosen_bssid' and 'chosen_channel'
        # directly if this script is part of a larger application or imported.
        # For example:
        # some_other_function(chosen_bssid, chosen_channel)
        pass # Placeholder, indicates successful selection without printing here

    else:
        # This message is kept as it indicates failure/cancellation
        print("\nNo AP was selected or process cancelled.")

    # The script will now exit. The chosen_bssid and chosen_channel values
    # were obtained but not printed in this final block.
    if not (chosen_bssid and chosen_channel) and not available_aps:
         sys.exit(1) # Exit with error code if scan failed initially
    elif not (chosen_bssid and chosen_channel):
         sys.exit(0) # Exit normally if user cancelled or selection failed after scan
    else:
         sys.exit(0) # Exit normally on successful selection