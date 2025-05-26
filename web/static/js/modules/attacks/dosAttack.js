/**
 * DOS Attack module
 */

/**
 * Generate HTML for deauth attack configuration
 * @param {Object} network - The selected network
 * @returns {string} HTML for the configuration form
 */
export function configureDosAttack(network) {
    return `
        <div class="alert alert-info">
            <p>
            <strong>DoS Attack Active:</strong> 
            Sending continuous deauth packets to disrupt ${network?.essid || 'target network'}</p>
            <p>
                <strong>Target BSSID:</strong> 
            ${network?.bssid || 'Not specified'}</p>
        </div>
    `;
} 