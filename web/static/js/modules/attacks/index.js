/**
 * Attacks Module - Main entry point for attack functionality
 */

import { attackApi } from '../api.js';
import { showAlert } from '../ui.js';
import { updateAttackStatus, updateAttackLog } from '../ui.js';
import { getState, setSelectedAttack, setAttackRunning, updateAttackLog as updateStateLog } from '../state.js';
import { configureDeauth } from './deauth.js';
import { configureHandshake } from './handshake.js';
import { configureEvilTwin } from './evilTwin.js';
import { configureDosAttack } from './dosAttack.js';
import { configureKarma } from './karmaAttack.js';
import { configureIcmpFlood } from './icmpFlood.js';

// Attack configuration functions map
const attackConfigFunctions = {
    'deauth': configureDeauth,
    'handshake': configureHandshake,
    'evil_twin': configureEvilTwin,
    'dos': configureDosAttack,
    'karma': configureKarma,
    'icmp_flood': configureIcmpFlood,
};

/**
 * Initialize attack functionality
 */
export function initAttacks() {
    // Add event listeners for attack type selection
    const attackOptions = document.querySelectorAll('.attack-option');
    attackOptions.forEach(option => {
        option.addEventListener('click', () => selectAttackType(option));
    });
    
    // Add event listener for start attack button
    const startAttackBtn = document.getElementById('start-attack-btn');
    if (startAttackBtn) {
        startAttackBtn.addEventListener('click', startAttack);
    }
    
    // Add event listener for stop attack button
    const stopAttackBtn = document.getElementById('stop-attack-btn');
    if (stopAttackBtn) {
        stopAttackBtn.addEventListener('click', stopAttack);
    }
}

/**
 * Select attack type
 * @param {HTMLElement} attackOption - The selected attack option element
 */
function selectAttackType(attackOption) {
    // Remove selection from all attack options
    document.querySelectorAll('.attack-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Add selection to clicked attack option
    attackOption.classList.add('selected');
    
    // Store selected attack type
    const attackType = attackOption.dataset.attack;
    setSelectedAttack(attackType);
    
    // Show attack-specific configuration options
    showAttackConfig(attackType);
    
    // Enable the start attack button
    const startAttackBtn = document.getElementById('start-attack-btn');
    if (startAttackBtn) {
        startAttackBtn.disabled = false;
    }
}

/**
 * Show configuration options specific to the selected attack
 * @param {string} attackType - The selected attack type
 */
function showAttackConfig(attackType) {
    const configContainer = document.getElementById('attack-config');
    if (!configContainer) return;
    
    // Get the configuration function for the selected attack type
    const configureFunction = attackConfigFunctions[attackType];
    
    if (configureFunction) {
        const state = getState();
        configContainer.innerHTML = configureFunction(state.selectedNetwork);
    } else {
        configContainer.innerHTML = '<div class="alert alert-warning">Please select a valid attack type</div>';
    }
}

/**
 * Start the selected attack
 */
export async function startAttack() {
    const state = getState();
    
    if (!state.selectedAttack) {
        showAlert('Please select an attack type', 'warning');
        return;
    }
    
    // Special handling for Karma attack since it doesn't need a real network
    let network = state.selectedNetwork;
    if (state.selectedAttack === 'karma') {
        const karmaConfig = getAttackConfig(state.selectedAttack);
        if (!karmaConfig.essid) {
            showAlert('Please select a target network from probe requests', 'warning');
            return;
        }
        // Create dummy network object for Karma attack
        network = {
            bssid: '00:11:22:33:44:55', // Dummy BSSID
            essid: karmaConfig.essid,    // Selected from probe requests
            channel: '1',                // Default channel
            encryption: 'WPA2',          // Default encryption
            signal: -50,                 // Dummy signal strength
            frequency: '2.4',            // Default frequency
            rates: ['1', '2', '5.5', '11', '6', '9', '12', '18', '24', '36', '48', '54'] // Common rates
        };
    } else if (!network) {
        showAlert('Please select a target network', 'warning');
        return;
    }
    
    // Collect attack configuration
    const attackConfig = getAttackConfig(state.selectedAttack);
    
    try {
        // Make API call to start attack
        const result = await attackApi.startAttack(
            network,
            state.selectedAttack,
            attackConfig
        );
        
        if (result.success) {
            setAttackRunning(true);
            showAlert('Attack started successfully', 'success');
            updateAttackStatus(true);
            
            // Redirect to results page
            window.location.href = '/results';
        } else {
            showAlert(`Failed to start attack: ${result.error}`, 'danger');
        }
    } catch (error) {
        console.error('Error starting attack:', error);
        showAlert('Error starting attack. Please try again.', 'danger');
    }
}

/**
 * Stop the running attack
 */
export async function stopAttack() {
    try {
        const result = await attackApi.stopAttack();
        
        if (result.success) {
            setAttackRunning(false);
            updateAttackStatus(false);
        } else {
            showAlert(`Failed to stop attack: ${result.error}`, 'danger');
        }
    } catch (error) {
        console.error('Error stopping attack:', error);
        showAlert('Error stopping attack. Please try again.', 'danger');
    }
}

/**
 * Get attack configuration based on selected attack type
 * @param {string} attackType - The selected attack type
 * @returns {Object} The attack configuration
 */
function getAttackConfig(attackType) {
    const config = {};
    
    switch(attackType) {
        case 'deauth':
            config.client = document.getElementById('deauth-client')?.value || 'FF:FF:FF:FF:FF:FF';
            config.count = parseInt(document.getElementById('deauth-count')?.value || '10');
            config.interval = parseFloat(document.getElementById('deauth-interval')?.value || '0.1');
            break;
            
        case 'handshake':
            config.wordlist = document.getElementById('handshake-wordlist')?.value || '/usr/share/wordlists/rockyou.txt';
            config.duration = parseInt(document.getElementById('handshake-duration')?.value || '5');
            break;
            
        case 'evil_twin':
            config.channel = parseInt(document.getElementById('evil-twin-channel')?.value || '1');
            config.captive_portal = document.getElementById('evil-twin-captive')?.value === 'true';
            break;
            
        case 'karma':
            config.essid = document.getElementById('karma-network')?.value;
            config.scan_duration = parseInt(document.getElementById('karma-duration')?.value || '20');
            break;

        case 'icmp_flood':
            const selectedDevice = document.querySelector('input[name="target_device"]:checked');
            if (!selectedDevice) {
                throw new Error('Please select a target device');
            }
            config.target_ip = selectedDevice.value;
            config.packet_size = parseInt(document.getElementById('packet_size')?.value || '56');
            config.interval = parseInt(document.getElementById('interval')?.value || '0');
            config.thread_count = parseInt(document.getElementById('thread_count')?.value || '4');
            break;
    }
    
    return config;
}

/**
 * Start monitoring attack status and log updates
 */
export function startAttackMonitoring() {
    // Check attack status first
    checkAttackStatus();
    
    // Set interval for updates
    const monitoringInterval = setInterval(async () => {
        const state = getState();
        
        if (!state.attackRunning) {
            clearInterval(monitoringInterval);
            return;
        }
        
        await updateAttackLogFromServer();
        await checkAttackStatus();
    }, 2000);
    
    return monitoringInterval;
}

/**
 * Check attack status from server
 */
async function checkAttackStatus() {
    try {
        const statusData = await attackApi.getStatus();
        setAttackRunning(statusData.running);
        updateAttackStatus(statusData.running);
    } catch (error) {
        console.error('Error checking attack status:', error);
    }
}

/**
 * Update attack log from server
 */
async function updateAttackLogFromServer() {
    try {
        const logData = await attackApi.getLog();
        updateStateLog(logData.log);
        updateAttackLog(logData.log);
    } catch (error) {
        console.error('Error updating attack log:', error);
    }
} 