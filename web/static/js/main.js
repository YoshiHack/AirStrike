// Main JavaScript for AirStrike Web Interface

// Global variables
let selectedNetwork = null;
let selectedAttack = null;
let attackRunning = false;
let logUpdateInterval = null;

// DOM Ready function
document.addEventListener('DOMContentLoaded', function() {
    // Initialize interface elements
    initializeInterface();
    
    // Add event listeners
    setupEventListeners();
});

// Initialize interface elements
function initializeInterface() {
    // Check if we're on the dashboard page
    if (document.getElementById('dashboard-stats')) {
        updateDashboardStats();
    }
    
    // Check if we're on the network scanner page
    if (document.getElementById('scan-networks-btn')) {
        // Auto-scan networks on page load
        scanNetworks();
    }
    
    // Check if we're on the attack configuration page
    if (document.getElementById('attack-options')) {
        // Load selected network info if available
        loadSelectedNetworkInfo();
    }
    
    // Check if we're on the results page
    if (document.getElementById('attack-log')) {
        // Start log updates if attack is running
        startLogUpdates();
    }
}

// Setup event listeners for interactive elements
function setupEventListeners() {
    // Scan networks button
    const scanBtn = document.getElementById('scan-networks-btn');
    if (scanBtn) {
        scanBtn.addEventListener('click', scanNetworks);
    }
    
    // Network selection
    const networkList = document.getElementById('network-list');
    if (networkList) {
        networkList.addEventListener('click', function(e) {
            const networkItem = e.target.closest('.network-item');
            if (networkItem) {
                selectNetwork(networkItem);
            }
        });
    }
    
    // Attack type selection
    const attackOptions = document.querySelectorAll('.attack-option');
    attackOptions.forEach(option => {
        option.addEventListener('click', function() {
            selectAttackType(option);
        });
    });
    
    // Start attack button
    const startAttackBtn = document.getElementById('start-attack-btn');
    if (startAttackBtn) {
        startAttackBtn.addEventListener('click', startAttack);
    }
    
    // Stop attack button
    const stopAttackBtn = document.getElementById('stop-attack-btn');
    if (stopAttackBtn) {
        stopAttackBtn.addEventListener('click', stopAttack);
    }
    
    // Interface selection
    const interfaceSelect = document.getElementById('interface-select');
    if (interfaceSelect) {
        interfaceSelect.addEventListener('change', function() {
            setInterface(this.value);
        });
    }
}

// Scan for available networks
function scanNetworks() {
    const scanBtn = document.getElementById('scan-networks-btn');
    const networkList = document.getElementById('network-list');
    
    if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.textContent = 'Scanning...';
    }
    
    if (networkList) {
        networkList.innerHTML = '<div class="network-item">Scanning for networks...</div>';
    }
    
    // Make API call to scan networks
    fetch('/scan_wifi')
        .then(response => response.json())
        .then(data => {
            displayNetworks(data);
            if (scanBtn) {
                scanBtn.disabled = false;
                scanBtn.textContent = 'Scan Networks';
            }
        })
        .catch(error => {
            console.error('Error scanning networks:', error);
            if (networkList) {
                networkList.innerHTML = '<div class="network-item error">Error scanning networks. Please try again.</div>';
            }
            if (scanBtn) {
                scanBtn.disabled = false;
                scanBtn.textContent = 'Scan Networks';
            }
        });
}

// Display scanned networks in the UI
function displayNetworks(networks) {
    const networkList = document.getElementById('network-list');
    if (!networkList) return;
    
    if (networks.length === 0) {
        networkList.innerHTML = '<div class="network-item">No networks found</div>';
        return;
    }
    
    let html = '';
    networks.forEach(network => {
        html += `
            <div class="network-item" data-bssid="${network.BSSID}" data-essid="${network.ESSID}" data-channel="${network.Channel}">
                <div class="network-name">${network.ESSID || 'Hidden Network'}</div>
                <div class="network-details">
                    <span class="network-bssid">${network.BSSID}</span>
                    <span class="network-channel">CH: ${network.Channel}</span>
                </div>
            </div>
        `;
    });
    
    networkList.innerHTML = html;
}

// Select a network from the list
function selectNetwork(networkItem) {
    // Remove selection from all networks
    document.querySelectorAll('.network-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Add selection to clicked network
    networkItem.classList.add('selected');
    
    // Store selected network data
    selectedNetwork = {
        bssid: networkItem.dataset.bssid,
        essid: networkItem.dataset.essid,
        channel: networkItem.dataset.channel
    };
    
    // Store in session storage for use across pages
    sessionStorage.setItem('selectedNetwork', JSON.stringify(selectedNetwork));
    
    // Enable the continue button
    const continueBtn = document.getElementById('continue-btn');
    if (continueBtn) {
        continueBtn.disabled = false;
    }
}

// Load selected network info from session storage
function loadSelectedNetworkInfo() {
    const networkInfo = document.getElementById('selected-network-info');
    if (!networkInfo) return;
    
    const storedNetwork = sessionStorage.getItem('selectedNetwork');
    if (storedNetwork) {
        selectedNetwork = JSON.parse(storedNetwork);
        networkInfo.innerHTML = `
            <div class="card">
                <div class="card-header">Selected Network</div>
                <div class="card-body">
                    <p><strong>SSID:</strong> ${selectedNetwork.essid || 'Hidden Network'}</p>
                    <p><strong>BSSID:</strong> ${selectedNetwork.bssid}</p>
                    <p><strong>Channel:</strong> ${selectedNetwork.channel}</p>
                </div>
            </div>
        `;
    } else {
        networkInfo.innerHTML = `
            <div class="alert alert-warning">
                No network selected. Please <a href="/scan">scan and select a network</a> first.
            </div>
        `;
    }
}

// Select attack type
function selectAttackType(attackOption) {
    // Remove selection from all attack options
    document.querySelectorAll('.attack-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Add selection to clicked attack option
    attackOption.classList.add('selected');
    
    // Store selected attack type
    selectedAttack = attackOption.dataset.attack;
    
    // Show attack-specific configuration options
    showAttackConfig(selectedAttack);
    
    // Enable the start attack button
    const startAttackBtn = document.getElementById('start-attack-btn');
    if (startAttackBtn) {
        startAttackBtn.disabled = false;
    }
}

// Show configuration options specific to the selected attack
function showAttackConfig(attackType) {
    const configContainer = document.getElementById('attack-config');
    if (!configContainer) return;
    
    let configHTML = '';
    
    switch(attackType) {
        case 'deauth':
            configHTML = `
                <div class="form-group">
                    <label for="deauth-client">Target Client MAC (optional):</label>
                    <input type="text" id="deauth-client" class="form-control" placeholder="FF:FF:FF:FF:FF:FF for all clients">
                </div>
                <div class="form-group">
                    <label for="deauth-count">Packet Count:</label>
                    <input type="number" id="deauth-count" class="form-control" value="10" min="1">
                </div>
                <div class="form-group">
                    <label for="deauth-interval">Interval (seconds):</label>
                    <input type="number" id="deauth-interval" class="form-control" value="0.1" min="0.1" step="0.1">
                </div>
            `;
            break;
            
        case 'handshake':
            configHTML = `
                <div class="form-group">
                    <label for="handshake-wordlist">Wordlist Path:</label>
                    <input type="text" id="handshake-wordlist" class="form-control" value="/usr/share/wordlists/rockyou.txt">
                </div>
                <div class="form-group">
                    <label for="handshake-duration">Capture Duration (minutes):</label>
                    <input type="number" id="handshake-duration" class="form-control" value="5" min="1">
                </div>
            `;
            break;
            
        case 'evil_twin':
            configHTML = `
                <div class="form-group">
                    <label for="evil-twin-channel">Channel:</label>
                    <input type="number" id="evil-twin-channel" class="form-control" value="${selectedNetwork ? selectedNetwork.channel : '1'}" min="1" max="14">
                </div>
                <div class="form-group">
                    <label for="evil-twin-captive">Enable Captive Portal:</label>
                    <select id="evil-twin-captive" class="form-control">
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
            `;
            break;
            
        default:
            configHTML = '<div class="alert alert-warning">Please select an attack type</div>';
    }
    
    configContainer.innerHTML = configHTML;
}

// Start the selected attack
function startAttack() {
    if (!selectedNetwork || !selectedAttack) {
        showAlert('Please select a network and attack type', 'warning');
        return;
    }
    
    // Collect attack configuration
    const attackConfig = getAttackConfig();
    
    // Make API call to start attack
    fetch('/start_attack', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            network: selectedNetwork,
            attack_type: selectedAttack,
            config: attackConfig
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            attackRunning = true;
            showAlert('Attack started successfully', 'success');
            updateAttackStatus(true);
            
            // Redirect to results page
            window.location.href = '/results';
        } else {
            showAlert(`Failed to start attack: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error starting attack:', error);
        showAlert('Error starting attack. Please try again.', 'danger');
    });
}

// Get attack configuration based on selected attack type
function getAttackConfig() {
    const config = {};
    
    switch(selectedAttack) {
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
    }
    
    return config;
}

// Stop the running attack
function stopAttack() {
    fetch('/stop_attack', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            attackRunning = false;
            showAlert('Attack stopped successfully', 'success');
            updateAttackStatus(false);
        } else {
            showAlert(`Failed to stop attack: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error stopping attack:', error);
        showAlert('Error stopping attack. Please try again.', 'danger');
    });
}

// Update attack status in UI
function updateAttackStatus(isRunning) {
    const startBtn = document.getElementById('start-attack-btn');
    const stopBtn = document.getElementById('stop-attack-btn');
    
    if (startBtn && stopBtn) {
        startBtn.disabled = isRunning;
        stopBtn.disabled = !isRunning;
    }
    
    const statusIndicator = document.getElementById('attack-status');
    if (statusIndicator) {
        statusIndicator.className = isRunning ? 'status-running' : 'status-stopped';
        statusIndicator.textContent = isRunning ? 'Running' : 'Stopped';
    }
}

// Start log updates for the results page
function startLogUpdates() {
    // Check attack status first
    fetch('/attack_status')
        .then(response => response.json())
        .then(data => {
            attackRunning = data.running;
            updateAttackStatus(attackRunning);
            
            if (attackRunning) {
                // Update progress and logs
                updateAttackProgress(data.progress);
                updateAttackLog();
                
                // Set interval for updates
                logUpdateInterval = setInterval(() => {
                    updateAttackLog();
                    fetch('/attack_status')
                        .then(response => response.json())
                        .then(statusData => {
                            attackRunning = statusData.running;
                            updateAttackStatus(attackRunning);
                            updateAttackProgress(statusData.progress);
                            
                            if (!attackRunning) {
                                clearInterval(logUpdateInterval);
                            }
                        });
                }, 2000);
            }
        });
}

// Update attack progress bar
function updateAttackProgress(progress) {
    const progressBar = document.getElementById('attack-progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
    
    const progressText = document.getElementById('attack-progress-text');
    if (progressText) {
        progressText.textContent = `${progress}%`;
    }
}

// Update attack log with latest entries
function updateAttackLog() {
    fetch('/attack_log')
        .then(response => response.json())
        .then(data => {
            const logContainer = document.getElementById('attack-log');
            if (logContainer) {
                let logHTML = '';
                data.log.forEach(entry => {
                    let className = '';
                    if (entry.includes('[+]')) className = 'success';
                    if (entry.includes('[-]')) className = 'error';
                    if (entry.includes('[!]')) className = 'warning';
                    
                    logHTML += `<div class="log-entry ${className}">${entry}</div>`;
                });
                
                logContainer.innerHTML = logHTML;
                logContainer.scrollTop = logContainer.scrollHeight; // Auto-scroll to bottom
            }
        });
}

// Update dashboard statistics
function updateDashboardStats() {
    fetch('/dashboard_stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('networks-count').textContent = data.networks_count;
            document.getElementById('attacks-count').textContent = data.attacks_count;
            document.getElementById('captures-count').textContent = data.captures_count;
        });
}

// Set wireless interface
function setInterface(interfaceName) {
    fetch('/set_interface', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            interface: interfaceName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(`Interface set to ${interfaceName}`, 'success');
        } else {
            showAlert(`Failed to set interface: ${data.error}`, 'danger');
        }
    });
}

// Show alert message
function showAlert(message, type) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type}`;
    alertElement.textContent = message;
    
    alertsContainer.appendChild(alertElement);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertElement.remove();
    }, 5000);
}