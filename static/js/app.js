/**
 * Globální JavaScript funkce pro aplikaci.
 */

/**
 * Zobrazí notifikaci uživateli.
 * @param {string} message - Text zprávy
 * @param {string} type - Typ notifikace: 'success', 'error', 'info'
 */
function showNotification(message, type = 'info') {
    // Vytvoření notifikačního elementu
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg max-w-md transition-all duration-300 transform translate-x-0`;
    
    // Barvy podle typu
    const colors = {
        success: 'bg-green-600 text-white',
        error: 'bg-red-600 text-white',
        info: 'bg-blue-600 text-white'
    };
    
    notification.className += ` ${colors[type] || colors.info}`;
    notification.textContent = message;
    
    // Přidání do DOM
    document.body.appendChild(notification);
    
    // Automatické odstranění po 5 sekundách
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);
}

/**
 * Zkopíruje text do schránky.
 * @param {string} text - Text ke zkopírování
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Zkopírováno do schránky', 'success');
    }).catch(() => {
        showNotification('Chyba při kopírování', 'error');
    });
}

// HTMX error handling
document.body.addEventListener('htmx:responseError', function(event) {
    const detail = event.detail;
    let message = 'Došlo k chybě';
    
    if (detail.xhr && detail.xhr.response) {
        try {
            const response = JSON.parse(detail.xhr.response);
            message = response.detail || message;
        } catch (e) {
            message = detail.xhr.statusText || message;
        }
    }
    
    showNotification(message, 'error');
});

// HTMX success handling
document.body.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.xhr && event.detail.xhr.status >= 200 && event.detail.xhr.status < 300) {
        // Kontrola, zda response obsahuje success zprávu
        const target = event.detail.target;
        if (target && target.dataset.successMessage) {
            showNotification(target.dataset.successMessage, 'success');
        }
    }
});
