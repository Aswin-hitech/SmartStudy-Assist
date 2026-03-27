/**
 * Global Javascript functions for SmartStudy AI
 */

// Central API Handler
async function api(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json'
    };
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };

    // If sending FormData instead of JSON, remove Content-Type
    if (options.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    
    try {
        const response = await fetch(url, config);
        
        if (response.status === 401) {
            window.location.href = '/login';
            return null;
        }
        
        // Handle Blob responses for PDF downloads
        if (options.isBlob) {
            if (!response.ok) throw new Error('File download failed');
            return await response.blob();
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Server responded with an error');
        }
        
        return data;
    } catch (error) {
        console.error(`API Error [${options.method || 'GET'} ${url}]:`, error);
        throw error;
    }
}

// Global Logout System
async function logout() {
    try {
        await api('/api/auth/logout', { method: 'POST' });
    } catch (err) {
        console.error("Logout error", err);
    } finally {
        window.location.href = '/login';
    }
}

// UI State Management - Button Loaders
function setButtonLoading(buttonId, isLoading, loadingText = "Processing...", iconClass = "fa-solid fa-spinner fa-spin") {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    
    if (isLoading) {
        btn.disabled = true;
        btn.dataset.originalHtml = btn.innerHTML;
        btn.innerHTML = `<i class="${iconClass}"></i> ${loadingText}`;
    } else {
        btn.disabled = false;
        if (btn.dataset.originalHtml) {
            btn.innerHTML = btn.dataset.originalHtml;
        }
    }
}

// Error Message Helper
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerText = message;
        el.classList.remove('hidden');
    } else {
        alert(message);
    }
}
