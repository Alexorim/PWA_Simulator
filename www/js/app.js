document.addEventListener('DOMContentLoaded', () => {
    const urlForm = document.getElementById('urlForm');
    const urlInput = document.getElementById('urlInput');
    const historyList = document.getElementById('historyList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const pwaViewer = document.getElementById('pwaViewer');
    const pwaIframe = document.getElementById('pwaIframe');
    const viewerTitle = document.getElementById('viewerTitle');
    const closeViewerBtn = document.getElementById('closeViewerBtn');

    const STORAGE_KEY = 'pwa_simulator_history';

    // Load initial history
    let history = loadHistory();
    renderHistory();

    // Form Submission
    urlForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const rawUrl = urlInput.value.trim();
        if (!rawUrl) return;

        const formattedUrl = formatUrl(rawUrl);
        saveUrlToHistory(formattedUrl);
        openUrl(formattedUrl);
    });

    // Clear History Button
    clearHistoryBtn.addEventListener('click', () => {
        history = [];
        saveHistory();
        renderHistory();
    });

    // Close In-App Iframe Viewer
    closeViewerBtn.addEventListener('click', () => {
        pwaViewer.classList.add('hidden');
        pwaIframe.src = '';
    });

    // Helper Functions
    function formatUrl(url) {
        let trimmed = url.trim();
        if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
            trimmed = 'https://' + trimmed;
        }
        return trimmed;
    }

    function loadHistory() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    }

    function saveHistory() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
        } catch (e) {
            console.error('Error al guardar historial:', e);
        }
    }

    function saveUrlToHistory(url) {
        // Remove duplicate if exists
        history = history.filter(item => item !== url);
        // Add to beginning
        history.unshift(url);
        // Limit to 30 items
        if (history.length > 30) {
            history.pop();
        }
        saveHistory();
        renderHistory();
    }

    function deleteHistoryItem(url) {
        history = history.filter(item => item !== url);
        saveHistory();
        renderHistory();
    }

    function renderHistory() {
        historyList.innerHTML = '';

        if (history.length === 0) {
            historyList.innerHTML = '<div class="empty-state">No hay sitios recientes.<br>Ingresa una URL para comenzar.</div>';
            clearHistoryBtn.classList.add('hidden');
            return;
        }

        clearHistoryBtn.classList.remove('hidden');

        history.forEach(url => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.innerHTML = `
                <div class="history-info">
                    <span>🌐</span>
                    <span class="history-url">${escapeHtml(url)}</span>
                </div>
                <button class="btn-icon delete-btn" title="Eliminar">🗑</button>
            `;

            // Click item to open
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('delete-btn')) return;
                urlInput.value = url;
                openUrl(url);
            });

            // Click delete button
            const deleteBtn = item.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteHistoryItem(url);
            });

            historyList.appendChild(item);
        });
    }

    function openUrl(url) {
        // Check if Capacitor Browser Plugin is available
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Browser) {
            window.Capacitor.Plugins.Browser.open({ url: url });
        } else if (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) {
            window.open(url, '_system');
        } else {
            // Fallback for local web testing or iframe mode
            viewerTitle.textContent = url;
            pwaIframe.src = url;
            pwaViewer.classList.remove('hidden');
        }
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
