// main.js - Shared utilities
function showAlert(message, type = 'error') {
    const alertBox = document.getElementById('alertBox');
    if (!alertBox) return;
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type}`;
    alertBox.style.display = 'block';
    // Auto hide after 5 seconds
    setTimeout(() => { alertBox.style.display = 'none'; }, 5000);
}

function showSuccess(message) {
    showAlert(message, 'success');
}

async function apiCall(endpoint, method, data = null) {
    const config = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    if (data) {
        config.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api/${endpoint}`, config);
        const text = await response.text();
        
        let result;
        try {
            result = JSON.parse(text);
        } catch(e) {
            throw new Error(`Server returned invalid JSON: ${text.substring(0, 100)}`);
        }

        if (!response.ok) {
            throw new Error(result.error || 'API request failed');
        }
        return result;
    } catch (error) {
        throw error;
    }
}
