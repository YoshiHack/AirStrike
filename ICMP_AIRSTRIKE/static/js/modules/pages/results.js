/**
 * Results Page Module
 */

import { startAttackMonitoring, stopAttack } from '../attacks/index.js';
import { socket } from '../api.js';
import { showAlert } from '../ui.js';
import { updateAttackStatus, updateAttackLog } from '../ui.js';
import { setAttackRunning, updateAttackLog as updateStateLog } from '../state.js';

/**
 * Initialize results page
 */
export function initResultsPage() {
    // Add event listener for stop attack button
    const stopAttackBtn = document.getElementById('stop-attack-btn');
    if (stopAttackBtn) {
        stopAttackBtn.addEventListener('click', stopAttack);
    }
    
    // Set up WebSocket event listeners for real-time updates
    setupWebSocketListeners();
    
    // Also start the polling as fallback
    const monitoringInterval = startAttackMonitoring();
    
    // Clean up when leaving the page
    window.addEventListener('beforeunload', () => {
        clearInterval(monitoringInterval);
    });
}

/**
 * Set up WebSocket event listeners for real-time updates
 */
function setupWebSocketListeners() {
    // Listen for attack log updates
    socket.on('attack_log', (data) => {
        console.log('Received attack log update:', data);
        // Add the new message to the log
        const logContainer = document.getElementById('attack-log');
        if (logContainer) {
            let className = '';
            if (data.message.includes('[+]')) className = 'success';
            if (data.message.includes('[-]')) className = 'error';
            if (data.message.includes('[!]')) className = 'warning';
            
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry ${className}`;
            logEntry.textContent = data.message;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight; // Auto-scroll to bottom
        }
    });
    
    // Listen for attack started event
    socket.on('attack_started', (data) => {
        console.log('Attack started:', data);
        setAttackRunning(true);
        updateAttackStatus(true);
        showAlert(`${data.attack_type} attack started on ${data.target_network.essid}`, 'success');
    });
    
    // Listen for attack stopped event
    socket.on('attack_stopped', () => {
        console.log('Attack stopped');
        setAttackRunning(false);
        updateAttackStatus(false);
        showAlert('Attack stopped successfully', 'success');
    });
    
    // Listen for attack error event
    socket.on('attack_error', (data) => {
        console.error('Attack error:', data.error);
        setAttackRunning(false);
        updateAttackStatus(false);
        showAlert(`Attack error: ${data.error}`, 'danger');
    });
} 