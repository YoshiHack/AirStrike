/**
 * ICMP Flood Attack Configuration Module
 */

import { attackApi } from '../api.js';
import { showAlert } from '../ui.js';

/**
 * Configure ICMP Flood attack
 * @param {Object} network - The target network
 * @returns {string} HTML for attack configuration
 */
export function configureIcmpFlood(network) {
    // Start device scanning
    loadNetworkDevices();
    
    return `
        <div class="attack-config-container">
            <h3>ICMP Flood Configuration</h3>
            
            <div class="form-group">
                <label>Target Device:</label>
                <div class="device-list-container">
                    <div id="device-list" class="device-list">
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="sr-only">Loading...</span>
                            </div>
                            <p>Scanning for devices...</p>
                        </div>
                    </div>
                    <button type="button" class="btn btn-secondary btn-sm mt-2" onclick="window.refreshDeviceList()">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                </div>
            </div>
            
            <div class="form-group">
                <label for="packet_size">Packet Size (bytes):</label>
                <input type="number" id="packet_size" class="form-control" 
                       value="56" min="32" max="65500">
                <small class="form-text text-muted">Default ICMP packet size is 56 bytes</small>
            </div>
            
            <div class="form-group">
                <label for="interval">Packet Interval (ms):</label>
                <input type="number" id="interval" class="form-control" 
                       value="0" min="0" max="1000">
                <small class="form-text text-muted">0 for maximum speed, or specify delay in milliseconds</small>
            </div>
            
            <div class="form-group">
                <label for="thread_count">Thread Count:</label>
                <input type="number" id="thread_count" class="form-control" 
                       value="4" min="1" max="16">
                <small class="form-text text-muted">Number of parallel threads for flooding</small>
            </div>
        </div>
    `;
}

/**
 * Load network devices
 */
async function loadNetworkDevices() {
    try {
        const response = await attackApi.getNetworkDevices();
        
        if (response.success) {
            updateDeviceList(response.devices);
        } else {
            showAlert('Failed to scan network: ' + response.error, 'danger');
            updateDeviceList([]);
        }
    } catch (error) {
        console.error('Error scanning network:', error);
        showAlert('Error scanning network. Please try again.', 'danger');
        updateDeviceList([]);
    }
}

/**
 * Update device list in UI
 * @param {Array} devices - List of discovered devices
 */
function updateDeviceList(devices) {
    const deviceList = document.getElementById('device-list');
    if (!deviceList) return;
    
    if (devices.length === 0) {
        deviceList.innerHTML = `
            <div class="alert alert-warning">
                No devices found on the network.
                <button type="button" class="btn btn-warning btn-sm ml-2" onclick="window.refreshDeviceList()">
                    Try Again
                </button>
            </div>
        `;
        return;
    }
    
    deviceList.innerHTML = devices.map(device => `
        <div class="device-item">
            <input type="radio" name="target_device" id="device_${device.ip}" 
                   value="${device.ip}" class="device-radio">
            <label for="device_${device.ip}" class="device-label">
                <div class="device-info">
                    <strong>${device.hostname}</strong>
                    <span class="device-ip">${device.ip}</span>
                    <small class="device-mac">${device.mac}</small>
                </div>
            </label>
        </div>
    `).join('');
}

/**
 * Refresh device list
 */
window.refreshDeviceList = function() {
    const deviceList = document.getElementById('device-list');
    if (deviceList) {
        deviceList.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
                <p>Scanning for devices...</p>
            </div>
        `;
    }
    loadNetworkDevices();
};

/**
 * Get ICMP Flood attack configuration
 * @returns {Object} Attack configuration
 */
export function getIcmpFloodConfig() {
    const selectedDevice = document.querySelector('input[name="target_device"]:checked');
    if (!selectedDevice) {
        throw new Error('Please select a target device');
    }
    
    const config = {
        target_ip: selectedDevice.value,
        packet_size: parseInt(document.getElementById('packet_size').value) || 56,
        interval: parseInt(document.getElementById('interval').value) || 0,
        thread_count: parseInt(document.getElementById('thread_count').value) || 4
    };
    
    // Validate configuration
    if (!config.target_ip) {
        throw new Error('Please select a target device');
    }
    if (config.packet_size < 32 || config.packet_size > 65500) {
        throw new Error('Packet size must be between 32 and 65500 bytes');
    }
    if (config.interval < 0 || config.interval > 1000) {
        throw new Error('Interval must be between 0 and 1000 milliseconds');
    }
    if (config.thread_count < 1 || config.thread_count > 16) {
        throw new Error('Thread count must be between 1 and 16');
    }
    
    return config;
} 