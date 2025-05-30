// airstrike/webapp/static/js/modules/api.js

// Socket.IO related code REMOVED
// export const socket = io(); // REMOVE THIS LINE

// showAlert can be imported from a ui.js or be a global function
// For simplicity, assuming showAlert is available globally or imported elsewhere.

async function _request(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP error ${response.status}` }));
            throw new Error(errorData.error || `HTTP error ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API ${method} error for ${url}:`, error);
        // showAlert(`API Error: ${error.message}`, 'danger'); // Handle UI alerts in calling code
        throw error;
    }
}

export async function apiGet(url) {
    return _request(url, 'GET');
}

export async function apiPost(url, data) {
    return _request(url, 'POST', data);
}

export const networkApi = {
    scanNetworks: () => apiGet('/scan/scan_wifi'), // Adjust URL if blueprint prefix changes
    checkInterfaceStatus: () => apiGet('/scan/scan_wifi?check_only=true'),
    setInterface: (interfaceName) => apiPost('/settings/set_interface', { interface: interfaceName })
};

export const attackApi = {
    startAttack: (network, attackType, config) =>
        apiPost('/attack/start', { network, attack_type: attackType, config }), // Adjusted URL
    // stopAttack: () => apiPost('/attack/stop', {}), // Implement this route and service
    getStatus: (attackId) => apiGet(`/attack/status/${attackId}`), // New endpoint for polling
    // getLog: (attackId) => apiGet(`/attack/log/${attackId}`) // Can be combined with getStatus
};

export const statsApi = {
    getDashboardStats: () => apiGet('/dashboard_stats') // Assuming this is on main_bp
};

// ... other API namespaces