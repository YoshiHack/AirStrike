/**
 * API Module - Handles all API calls with consistent error handling
 */

import { showAlert } from './ui.js';

// Initialize Socket.IO connection
export const socket = io();

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server via WebSocket');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

/**
 * Handle sudo authentication redirect
 * @param {Object} data - Response data containing redirect URL
 */
function handleSudoAuthRedirect(data) {
    if (data && data.redirect) {
        // Show message before redirecting
        showSudoRequiredMessage();
        // Redirect after a short delay to allow message to be seen
        setTimeout(() => {
            window.location.href = data.redirect;
        }, 500);
        return true;
    }
    return false;
}

/**
 * Make a GET request to the specified endpoint
 * @param {string} url - The endpoint URL
 * @returns {Promise} - Promise resolving to the JSON response
 */
export async function apiGet(url) {
    try {
        const response = await fetch(url);
        
        // Handle sudo authentication required
        if (response.status === 401) {
            const data = await response.json();
            if (data.error === 'sudo_auth_required') {
                handleSudoAuthRedirect(data);
                return null;
            }
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API GET error for ${url}:`, error);
        showAlert(`API Error: ${error.message}`, 'danger');
        throw error;
    }
}

/**
 * Make a POST request to the specified endpoint
 * @param {string} url - The endpoint URL
 * @param {Object} data - The data to send in the request body
 * @returns {Promise} - Promise resolving to the JSON response
 */
export async function apiPost(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        // Handle sudo authentication required
        if (response.status === 401) {
            const responseData = await response.json();
            if (responseData.error === 'sudo_auth_required') {
                handleSudoAuthRedirect(responseData);
                return null;
            }
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API POST error for ${url}:`, error);
        showAlert(`API Error: ${error.message}`, 'danger');
        throw error;
    }
}

/**
 * Show a message to the user that sudo authentication is required
 */
function showSudoRequiredMessage() {
    // Create an alert element if it doesn't exist
    let alertElement = document.getElementById('sudo-auth-alert');
    if (!alertElement) {
        alertElement = document.createElement('div');
        alertElement.id = 'sudo-auth-alert';
        alertElement.className = 'alert alert-info';
        alertElement.innerHTML = `
            <strong>Administrator privileges required</strong>
            <p>This operation requires administrator privileges. You will be redirected to the authentication page.</p>
        `;
        
        // Insert at the top of the page
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertElement, container.firstChild);
        } else {
            document.body.insertBefore(alertElement, document.body.firstChild);
        }
    }
}

/**
 * Network API functions
 */
export const networkApi = {
    /**
     * Scan for available WiFi networks
     * @returns {Promise<Array>} Array of network objects
     */
    async scanNetworks() {
        try {
            const response = await fetch('/scan_wifi');
            
            // Handle sudo authentication required
            if (response.status === 401) {
                const data = await response.json();
                if (data.error === 'sudo_auth_required') {
                    handleSudoAuthRedirect(data);
                    return [];
                }
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success === false) {
                // Handle other error responses
                if (data.error) {
                    throw new Error(data.error || 'Unknown error scanning networks');
                }
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            showAlert(`Network scan error: ${error.message}`, 'danger');
            throw error;
        }
    },
    
    /**
     * Check interface status
     * @returns {Promise<Object>} Interface status data
     */
    async checkInterfaceStatus() {
        try {
            const response = await fetch('/scan_wifi?check_only=true');
            
            // Handle sudo authentication required
            if (response.status === 401) {
                const data = await response.json();
                if (data.error === 'sudo_auth_required') {
                    handleSudoAuthRedirect(data);
                    return { success: false, error: 'Authentication required' };
                }
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showAlert(`Interface status check error: ${error.message}`, 'danger');
            return { 
                success: false, 
                error: error.message,
                interface_status: {
                    exists: false,
                    name: 'unknown',
                    is_wireless: false
                }
            };
        }
    },
    
    /**
     * Set the wireless interface
     * @param {string} interfaceName - The name of the interface to use
     * @returns {Promise} - Promise resolving to the result
     */
    setInterface: (interfaceName) => apiPost('/set_interface', { interface: interfaceName })
};

/**
 * API functions for attacks
 */
export const attackApi = {
    /**
     * Start an attack
     * @param {Object} network - The target network
     * @param {string} attackType - The type of attack
     * @param {Object} config - The attack configuration
     * @returns {Promise} - Promise resolving to the result
     */
    startAttack: (network, attackType, config) => 
        apiPost('/start_attack', { network, attack_type: attackType, config }),
    
    /**
     * Stop the running attack
     * @returns {Promise} - Promise resolving to the result
     */
    stopAttack: () => apiPost('/stop_attack', {}),
    
    /**
     * Get the status of the running attack
     * @returns {Promise} - Promise resolving to the attack status
     */
    getStatus: () => apiGet('/attack_status'),
    
    /**
     * Get the attack log
     * @returns {Promise} - Promise resolving to the attack log
     */
    getLog: () => apiGet('/attack_log')
};

/**
 * API functions for dashboard statistics
 */
export const statsApi = {
    /**
     * Get dashboard statistics
     * @returns {Promise} - Promise resolving to the dashboard statistics
     */
    getDashboardStats: () => apiGet('/dashboard_stats')
}; 