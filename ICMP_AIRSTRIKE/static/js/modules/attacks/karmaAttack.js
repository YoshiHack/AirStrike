/**
 * Karma Attack Module
 */

import { scanApi } from '../api.js';
import { showAlert } from '../ui.js';

/**
 * Generate HTML for karma attack configuration
 * @param {Object} network - The selected network
 * @returns {string} HTML for the configuration form
 */
export function configureKarma(network) {
    return `
        <div class="form-group">
            <label for="karma-duration">Scan Duration (seconds):</label>
            <input type="number" id="karma-duration" class="form-control" value="20" min="5" max="60">
            <small class="form-text text-muted">How long to scan for probe requests (5-60 seconds)</small>
        </div>
        <div class="form-group">
            <label for="karma-network">Target Network (from probe requests):</label>
            <div class="input-group">
                <select id="karma-network" class="form-control">
                    <option value="">No networks scanned yet</option>
                </select>
                <div class="input-group-append">
                    <button id="scan-probe-btn" class="btn btn-primary" onclick="window.startKarmaScan()">
                        Scan <span id="probe-scan-status"></span>
                    </button>
                </div>
            </div>
            <small id="scan-timer" class="form-text text-muted"></small>
        </div>
        <div class="alert alert-info">
            <p><strong>Karma Attack:</strong> Creates rogue access points based on probe requests to capture client connections.</p>
            <p>Set duration and click "Scan" to discover networks sending probe requests.</p>
        </div>
    `;
}

/**
 * Get karma attack configuration
 * @returns {Object} The attack configuration
 */
export function getKarmaConfig() {
    const networkSelect = document.getElementById('karma-network');
    const durationInput = document.getElementById('karma-duration');
    
    if (!networkSelect || !networkSelect.value) {
        throw new Error('Please select a target network from probe requests');
    }
    
    return {
        essid: networkSelect.value,
        scan_duration: parseInt(durationInput?.value || '20', 10)
    };
}

/**
 * Start a single probe request scan
 */
async function startProbeScanning() {
    const networkSelect = document.getElementById('karma-network');
    const statusSpan = document.getElementById('probe-scan-status');
    const scanButton = document.getElementById('scan-probe-btn');
    const durationInput = document.getElementById('karma-duration');
    const timerSpan = document.getElementById('scan-timer');
    
    if (!networkSelect || !statusSpan || !scanButton || !durationInput || !timerSpan) return;
    
    try {
        // Get scan duration
        const duration = parseInt(durationInput.value || '20', 10);
        if (duration < 5 || duration > 60) {
            showAlert('Scan duration must be between 5 and 60 seconds', 'warning');
            return;
        }
        
        // Update UI to show scanning
        statusSpan.textContent = ' ⚡';
        scanButton.disabled = true;
        durationInput.disabled = true;
        networkSelect.innerHTML = '<option value="">Scanning...</option>';
        
        // Start countdown timer
        let timeLeft = duration;
        const timer = setInterval(() => {
            timeLeft--;
            timerSpan.textContent = `Scanning... ${timeLeft}s remaining`;
            if (timeLeft <= 0) {
                clearInterval(timer);
                timerSpan.textContent = '';
            }
        }, 1000);
        
        // Perform the scan with duration
        const ssids = await scanApi.sniffProbeRequests(duration);
        
        // Clear existing options
        networkSelect.innerHTML = '';
        
        // Handle error response
        if (ssids && ssids.success === false) {
            networkSelect.innerHTML = '<option value="">Error scanning networks</option>';
            statusSpan.textContent = ' ⚠';
            return;
        }
        
        // Handle empty response
        if (!Array.isArray(ssids) || ssids.length === 0) {
            networkSelect.innerHTML = '<option value="">No networks found</option>';
            statusSpan.textContent = ' (0)';
            return;
        }
        
        // Add default option
        networkSelect.innerHTML = '<option value="">Select a network...</option>';
        
        // Create a Set to store unique SSIDs
        const uniqueSsids = new Set();
        
        ssids.forEach(ssid => {
            if (typeof ssid === 'string' && ssid.trim()) {
                uniqueSsids.add(ssid.trim());
            }
        });
        
        // Convert Set back to Array and sort alphabetically
        Array.from(uniqueSsids)
            .sort()
            .forEach(ssid => {
                const option = document.createElement('option');
                option.value = ssid;
                option.textContent = ssid;
                networkSelect.appendChild(option);
            });
            
        // Update status with count
        statusSpan.textContent = ` (${uniqueSsids.size})`;
        
    } catch (error) {
        console.error('Error scanning for networks:', error);
        showAlert('Error scanning for networks. Please try again.', 'danger');
        statusSpan.textContent = ' ⚠';
        networkSelect.innerHTML = '<option value="">Error scanning</option>';
    } finally {
        // Re-enable controls
        scanButton.disabled = false;
        durationInput.disabled = false;
        timerSpan.textContent = '';
    }
}

// Export the scanning function to make it available to the onclick handler
window.startKarmaScan = startProbeScanning;