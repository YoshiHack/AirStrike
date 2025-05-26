/**
 * Karma Attack Module
 */

/**
 * Generate HTML for Karma attack configuration
 * @param {Object} network - The selected network (optional)
 * @returns {string} HTML for the configuration form
 */
export function configureKarma(network) {
    return `
        <div class="card mt-4">
            <div class="card-header">Available Networks</div>
            <div class="card-body">
                <div id="network-list" class="network-list">
                    <div class="network-item">
                        <div calss="network-name">Infinix HOT 30</div>
                    </div>
                    <div class="network-item">
                        <div calss="network-name">Umniah_8B715</div>
                    </div>
                    <div class="network-item">
                        <div calss="network-name">Umniah_4D686-EXT</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="form-group">
            <label for="karma-channel">Channel:</label>
            <input type="number" id="karma-channel" class="form-control" value="6" min="1" max="14">
        </div>
        <div class="form-group">
            <label for="karma-interface">Interface:</label>
            <select id="karma-interface" class="form-control">
                <option value="wlan0">wlan0</option>
                <option value="wlan1">wlan1</option>
            </select>
        </div>
        <div class="alert alert-warning">
            <p><strong>Karma Attack:</strong> Creates fake APs that respond to all probe requests.</p>
            <p><strong>Warning:</strong> Devices may auto-connect if they've previously trusted the SSID.</p>
            ${network ? `<p><strong>Targeting:</strong> ${network.essid || 'Hidden Network'} (${network.bssid || 'Unknown'})</p>` : ''}
        </div>
    `;
}