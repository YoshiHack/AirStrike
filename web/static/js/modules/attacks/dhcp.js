/**
 * DHCP Attack Module - Handles DHCP attack configuration and UI
 */

/**
 * Generate HTML for DHCP attack configuration
 * @param {Object} network - The selected network
 * @returns {string} HTML for the configuration form
 */
export function configureDhcp(network) {
    return `
        <div class="form-group">
            <label for="dhcp-subtype">DHCP Attack Type:</label>
            <select id="dhcp-subtype" class="form-control">
                <option value="starvation">DHCP Starvation</option>
                <option value="rogue_server">Rogue DHCP Server</option>
                <option value="spoofing">DHCP Spoofing</option>
            </select>
            <small class="form-text text-muted">Select the type of DHCP attack to perform</small>
        </div>
        
        <!-- DHCP Starvation Configuration -->
        <div id="starvation-config" class="attack-subconfig">
            <div class="form-group">
                <label for="dhcp-target-count">Target Request Count:</label>
                <input type="number" id="dhcp-target-count" class="form-control" value="100" min="10" max="1000">
                <small class="form-text text-muted">Number of DHCP requests to send (10-1000)</small>
            </div>
        </div>
        
        <!-- Rogue DHCP Server Configuration -->
        <div id="rogue_server-config" class="attack-subconfig" style="display: none;">
            <div class="form-group">
                <label for="dhcp-rogue-ip">Rogue Server IP:</label>
                <input type="text" id="dhcp-rogue-ip" class="form-control" value="192.168.1.1" placeholder="192.168.1.1">
                <small class="form-text text-muted">IP address for the rogue DHCP server</small>
            </div>
            <div class="form-group">
                <label for="dhcp-gateway-ip">Gateway IP:</label>
                <input type="text" id="dhcp-gateway-ip" class="form-control" value="192.168.1.1" placeholder="192.168.1.1">
                <small class="form-text text-muted">Gateway IP to advertise to clients</small>
            </div>
            <div class="form-group">
                <label for="dhcp-dns-servers">DNS Servers:</label>
                <input type="text" id="dhcp-dns-servers" class="form-control" value="8.8.8.8,1.1.1.1" placeholder="8.8.8.8,1.1.1.1">
                <small class="form-text text-muted">Comma-separated list of DNS servers</small>
            </div>
        </div>
        
        <!-- DHCP Spoofing Configuration -->
        <div id="spoofing-config" class="attack-subconfig" style="display: none;">
            <div class="form-group">
                <label for="dhcp-target-mac">Target MAC Address:</label>
                <input type="text" id="dhcp-target-mac" class="form-control" value="all" placeholder="all or specific MAC">
                <small class="form-text text-muted">Target client MAC address or "all" for all clients</small>
            </div>
            <div class="form-group">
                <label for="dhcp-malicious-gateway">Malicious Gateway:</label>
                <input type="text" id="dhcp-malicious-gateway" class="form-control" value="192.168.1.100" placeholder="192.168.1.100">
                <small class="form-text text-muted">Malicious gateway IP to inject</small>
            </div>
            <div class="form-group">
                <label for="dhcp-malicious-dns">Malicious DNS:</label>
                <input type="text" id="dhcp-malicious-dns" class="form-control" value="192.168.1.100" placeholder="192.168.1.100">
                <small class="form-text text-muted">Malicious DNS server to inject</small>
            </div>
        </div>
    `;
}

/**
 * Get DHCP attack configuration from form inputs
 * @returns {Object} Configuration object for the DHCP attack
 */
export function getDhcpConfig() {
    const subtype = document.getElementById('dhcp-subtype').value;
    const config = { subtype };
    
    if (subtype === 'starvation') {
        config.target_count = parseInt(document.getElementById('dhcp-target-count').value) || 100;
    } else if (subtype === 'rogue_server') {
        config.rogue_ip = document.getElementById('dhcp-rogue-ip').value || '192.168.1.1';
        config.gateway_ip = document.getElementById('dhcp-gateway-ip').value || '192.168.1.1';
        const dnsServers = document.getElementById('dhcp-dns-servers').value || '8.8.8.8,1.1.1.1';
        config.dns_servers = dnsServers.split(',').map(ip => ip.trim());
    } else if (subtype === 'spoofing') {
        config.target_mac = document.getElementById('dhcp-target-mac').value || 'all';
        config.malicious_gateway = document.getElementById('dhcp-malicious-gateway').value || '192.168.1.100';
        config.malicious_dns = document.getElementById('dhcp-malicious-dns').value || '192.168.1.100';
    }
    
    return config;
}

/**
 * Initialize DHCP attack configuration UI
 */
export function initDhcpConfig() {
    // Handle subtype selection change
    const subtypeSelect = document.getElementById('dhcp-subtype');
    if (subtypeSelect) {
        subtypeSelect.addEventListener('change', function() {
            showDhcpSubconfig(this.value);
        });
        
        // Show initial configuration
        showDhcpSubconfig(subtypeSelect.value);
    }
}

/**
 * Show the appropriate sub-configuration based on attack subtype
 * @param {string} subtype - The selected DHCP attack subtype
 */
function showDhcpSubconfig(subtype) {
    // Hide all sub-configurations
    const subconfigs = document.querySelectorAll('.attack-subconfig');
    subconfigs.forEach(config => {
        config.style.display = 'none';
    });
    
    // Show the selected sub-configuration
    const selectedConfig = document.getElementById(`${subtype}-config`);
    if (selectedConfig) {
        selectedConfig.style.display = 'block';
    }
}

/**
 * Validate DHCP attack configuration
 * @returns {Object} Validation result with success flag and error message
 */
export function validateDhcpConfig() {
    const subtype = document.getElementById('dhcp-subtype').value;
    
    if (subtype === 'starvation') {
        const targetCount = parseInt(document.getElementById('dhcp-target-count').value);
        if (isNaN(targetCount) || targetCount < 10 || targetCount > 1000) {
            return {
                success: false,
                error: 'Target count must be between 10 and 1000'
            };
        }
    } else if (subtype === 'rogue_server') {
        const rogueIp = document.getElementById('dhcp-rogue-ip').value;
        const gatewayIp = document.getElementById('dhcp-gateway-ip').value;
        
        if (!isValidIP(rogueIp)) {
            return {
                success: false,
                error: 'Invalid rogue server IP address'
            };
        }
        
        if (!isValidIP(gatewayIp)) {
            return {
                success: false,
                error: 'Invalid gateway IP address'
            };
        }
        
        const dnsServers = document.getElementById('dhcp-dns-servers').value;
        const dnsArray = dnsServers.split(',').map(ip => ip.trim());
        for (const dns of dnsArray) {
            if (!isValidIP(dns)) {
                return {
                    success: false,
                    error: `Invalid DNS server IP: ${dns}`
                };
            }
        }
    } else if (subtype === 'spoofing') {
        const targetMac = document.getElementById('dhcp-target-mac').value;
        const maliciousGateway = document.getElementById('dhcp-malicious-gateway').value;
        const maliciousDns = document.getElementById('dhcp-malicious-dns').value;
        
        if (targetMac !== 'all' && !isValidMAC(targetMac)) {
            return {
                success: false,
                error: 'Invalid target MAC address (use "all" or valid MAC format)'
            };
        }
        
        if (!isValidIP(maliciousGateway)) {
            return {
                success: false,
                error: 'Invalid malicious gateway IP address'
            };
        }
        
        if (!isValidIP(maliciousDns)) {
            return {
                success: false,
                error: 'Invalid malicious DNS IP address'
            };
        }
    }
    
    return { success: true };
}

/**
 * Validate IP address format
 * @param {string} ip - IP address to validate
 * @returns {boolean} True if valid IP address
 */
function isValidIP(ip) {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipRegex.test(ip);
}

/**
 * Validate MAC address format
 * @param {string} mac - MAC address to validate
 * @returns {boolean} True if valid MAC address
 */
function isValidMAC(mac) {
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    return macRegex.test(mac);
}

/**
 * Get DHCP attack description for display
 * @param {string} subtype - The DHCP attack subtype
 * @returns {string} Description of the attack
 */
export function getDhcpDescription(subtype) {
    const descriptions = {
        'starvation': 'Exhausts the DHCP server\'s IP address pool by sending multiple DHCP requests with fake MAC addresses',
        'rogue_server': 'Sets up a malicious DHCP server to provide false network configuration to clients',
        'spoofing': 'Intercepts and modifies DHCP responses to redirect client traffic through malicious gateways'
    };
    
    return descriptions[subtype] || 'DHCP attack to disrupt network connectivity';
}
