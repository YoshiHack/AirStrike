// static/js/modules/pages/results.js (Conceptual change)
// ... imports ...
import { attackApi } from '../api.js'; // Your modified api.js
import { updateAttackLog, updateAttackStatus } from '../ui.js'; // Your existing ui.js

let currentAttackId = null; // Store this when an attack starts
let pollingInterval = null;

export function initResultsPage() {
    // ... existing setup ...

    // Assume currentAttackId is somehow set, e.g., from session storage or query param
    // after starting an attack.
    // For this example, let's say it's hardcoded or fetched differently.
    // currentAttackId = sessionStorage.getItem('currentAttackId'); 

    if (currentAttackId) {
        startPollingAttackStatus(currentAttackId);
    } else {
        // Display "No active attack" or fetch last attack status
        updateAttackLog(["No active attack selected for real-time updates."]);
    }

    // Modify stopAttackBtn to use API and clear polling
    const stopAttackBtn = document.getElementById('stop-attack-btn');
    if (stopAttackBtn) {
        stopAttackBtn.addEventListener('click', async () => {
            if (currentAttackId) {
                // await attackApi.stopAttack(currentAttackId); // Implement this
                stopPolling();
                showAlert('Stop request sent (implement actual stop).', 'info');
            }
        });
    }
}

function startPollingAttackStatus(attackId) {
    stopPolling(); // Clear any existing interval

    pollingInterval = setInterval(async () => {
        try {
            const response = await attackApi.getStatus(attackId);
            if (response.success) {
                updateAttackLog(response.logs || ["Waiting for logs..."]);
                updateAttackStatus(response.status.status === 'running', response.status); // Adapt ui.js if needed

                if (response.status.status === 'completed' || response.status.status === 'failed' || response.status.status === 'stopped') {
                    stopPolling();
                    showAlert(`Attack ${response.status.status}.`, 'info');
                }
            } else {
                // showAlert(`Error polling status: ${response.error}`, 'warning');
                // stopPolling(); // Optionally stop on error
            }
        } catch (error) {
            console.error('Polling error:', error);
            // showAlert('Error fetching attack status.', 'danger');
            // stopPolling(); // Optionally stop on error
        }
    }, 3000); // Poll every 3 seconds
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Make sure to set currentAttackId when an attack starts.
// For example, after a successful call to attackApi.startAttack,
// you could store the returned attack_id in sessionStorage and retrieve it here.