document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const urlForm = document.getElementById('urlForm');
    const urlInput = document.getElementById('urlInput');
    const historyList = document.getElementById('historyList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const pwaViewer = document.getElementById('pwaViewer');
    const pwaIframe = document.getElementById('pwaIframe');
    const viewerTitle = document.getElementById('viewerTitle');
    const closeViewerBtn = document.getElementById('closeViewerBtn');
    const noticeOpenBtn = document.getElementById('noticeOpenBtn');

    // Menu Elements
    const viewerMenuBtn = document.getElementById('viewerMenuBtn');
    const viewerDropdown = document.getElementById('viewerDropdown');
    const viewerReloadBtn = document.getElementById('viewerReloadBtn');
    const viewerInstallBtn = document.getElementById('viewerInstallBtn');
    const viewerDevtoolsBtn = document.getElementById('viewerDevtoolsBtn');
    const viewerExternalBtn = document.getElementById('viewerExternalBtn');
    const viewerCloseMenuBtn = document.getElementById('viewerCloseMenuBtn');

    // DevTools Elements
    const devToolsModal = document.getElementById('devToolsModal');
    const closeDevtoolsBtn = document.getElementById('closeDevtoolsBtn');
    const tabConsole = document.getElementById('tabConsole');
    const tabElements = document.getElementById('tabElements');
    const tabNetwork = document.getElementById('tabNetwork');
    const devConsoleView = document.getElementById('devConsoleView');
    const devElementsView = document.getElementById('devElementsView');
    const devNetworkView = document.getElementById('devNetworkView');
    const consoleOutput = document.getElementById('consoleOutput');
    const clearConsoleBtn = document.getElementById('clearConsoleBtn');
    const elementsOutput = document.getElementById('elementsOutput');
    const refreshDomBtn = document.getElementById('refreshDomBtn');
    const pwaInfoOutput = document.getElementById('pwaInfoOutput');

    const STORAGE_KEY = 'pwa_simulator_history';
    let currentUrl = '';
    let deferredPrompt = null;
    let capturedLogs = [];

    // Capture browser beforeinstallprompt
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        console.log('[PWA] Evento beforeinstallprompt capturado');
        appendLog('info', 'PWA Simulator está listo para ser instalado como aplicación.');
    });

    // 1. Iniciar Animación de Red Neuronal en Fondo
    initNeuralNetworkCanvas();

    // 2. Load initial history
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
    closeViewerBtn.addEventListener('click', closeViewer);
    viewerCloseMenuBtn.addEventListener('click', () => {
        hideDropdown();
        closeViewer();
    });

    function closeViewer() {
        pwaViewer.classList.add('hidden');
        pwaIframe.src = '';
        currentUrl = '';
        hideDropdown();
        devToolsModal.classList.add('hidden');
    }

    // Toggle Dropdown Menu
    viewerMenuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        viewerDropdown.classList.toggle('hidden');
    });

    // Close Dropdown on outside click
    document.addEventListener('click', (e) => {
        if (viewerDropdown && !viewerDropdown.contains(e.target) && e.target !== viewerMenuBtn) {
            hideDropdown();
        }
    });

    function hideDropdown() {
        if (viewerDropdown) viewerDropdown.classList.add('hidden');
    }

    // Reload Action
    viewerReloadBtn.addEventListener('click', () => {
        hideDropdown();
        if (currentUrl && pwaIframe) {
            appendLog('info', `Recargando vista: ${currentUrl}`);
            pwaIframe.src = currentUrl;
        }
    });

    // Install Action in Viewer
    viewerInstallBtn.addEventListener('click', () => {
        hideDropdown();
        installPwa(currentUrl);
    });

    // Open External in Popup
    viewerExternalBtn.addEventListener('click', () => {
        hideDropdown();
        if (currentUrl) {
            openInStandaloneWindow(currentUrl);
        }
    });

    noticeOpenBtn.addEventListener('click', () => {
        if (currentUrl) {
            openInStandaloneWindow(currentUrl);
        }
    });

    // DevTools Toggle
    viewerDevtoolsBtn.addEventListener('click', () => {
        hideDropdown();
        toggleDevTools();
    });

    closeDevtoolsBtn.addEventListener('click', () => {
        devToolsModal.classList.add('hidden');
    });

    // DevTools Tabs Switching
    tabConsole.addEventListener('click', () => switchTab('console'));
    tabElements.addEventListener('click', () => {
        switchTab('elements');
        inspectDom();
    });
    tabNetwork.addEventListener('click', () => {
        switchTab('network');
        inspectPwaMetadata();
    });

    function switchTab(tab) {
        tabConsole.classList.toggle('active', tab === 'console');
        tabElements.classList.toggle('active', tab === 'elements');
        tabNetwork.classList.toggle('active', tab === 'network');

        devConsoleView.classList.toggle('hidden', tab !== 'console');
        devElementsView.classList.toggle('hidden', tab !== 'elements');
        devNetworkView.classList.toggle('hidden', tab !== 'network');
    }

    function toggleDevTools() {
        const isHidden = devToolsModal.classList.toggle('hidden');
        if (!isHidden) {
            renderLogs();
            inspectPwaMetadata();
        }
    }

    clearConsoleBtn.addEventListener('click', () => {
        capturedLogs = [];
        consoleOutput.innerHTML = '<div class="empty-state">Consola limpia.</div>';
    });

    refreshDomBtn.addEventListener('click', inspectDom);

    // Logging & Console Interception
    function appendLog(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        capturedLogs.push({ level, message, timestamp });
        if (capturedLogs.length > 200) capturedLogs.shift();
        renderLogs();
    }

    function renderLogs() {
        if (!consoleOutput) return;
        if (capturedLogs.length === 0) {
            consoleOutput.innerHTML = '<div class="empty-state">Esperando mensajes o eventos de la página...</div>';
            return;
        }

        consoleOutput.innerHTML = capturedLogs.map(log => `
            <div class="log-entry ${log.level}">
                <span class="log-time">[${log.timestamp}]</span>
                <span class="log-msg">${escapeHtml(String(log.message))}</span>
            </div>
        `).join('');

        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    // Intercept Window Messages from iframe
    window.addEventListener('message', (event) => {
        if (event.data && typeof event.data === 'object') {
            appendLog('info', `Mensaje recibido [${event.origin}]: ${JSON.stringify(event.data)}`);
        } else if (typeof event.data === 'string') {
            appendLog('log', `Evento postMessage: ${event.data}`);
        }
    });

    // Inspect iframe DOM (or fallback if cross-origin)
    function inspectDom() {
        elementsOutput.textContent = 'Analizando estructura...';
        try {
            if (pwaIframe.contentDocument) {
                const doc = pwaIframe.contentDocument;
                const title = doc.title || 'Sin título';
                const links = Array.from(doc.querySelectorAll('link')).map(l => l.outerHTML).join('\n');
                const metas = Array.from(doc.querySelectorAll('meta')).map(m => m.outerHTML).join('\n');
                const scripts = Array.from(doc.querySelectorAll('script[src]')).map(s => s.outerHTML).join('\n');
                const bodyPreview = doc.body ? doc.body.innerHTML.slice(0, 3000) : '';

                elementsOutput.textContent = `<!-- Titulo: ${title} -->\n\n<!-- Metadatos & Links -->\n${links}\n${metas}\n\n<!-- Scripts -->\n${scripts}\n\n<!-- Preview Body -->\n${bodyPreview}`;
                appendLog('info', 'Estructura DOM leída con éxito');
            } else {
                showCrossOriginDomNotice();
            }
        } catch (e) {
            showCrossOriginDomNotice();
        }
    }

    function showCrossOriginDomNotice() {
        elementsOutput.textContent = `<!DOCTYPE html>
<!-- DOM Protegido por Cross-Origin (CORS / Same-Origin Policy) -->
<html lang="es">
<head>
    <title>${escapeHtml(currentUrl)}</title>
    <!-- Los navegadores impiden inspeccionar el árbol interno directo -->
    <!-- de sitios en otros dominios dentro de un iframe por seguridad. -->
</head>
<body>
    <div id="pwa-simulated-root" data-url="${escapeHtml(currentUrl)}">
        <!-- Simulación Activa en PWA Simulator -->
        <!-- Usa el menú ⋮ > "Abrir en ventana PWA" para depurar con DevTools nativas (F12) -->
    </div>
</body>
</html>`;
        appendLog('warn', 'Aviso: El sitio tiene políticas de origen cruzado (CORS). Se aplica vista protegida.');
    }

    function inspectPwaMetadata() {
        if (!pwaInfoOutput) return;
        const domain = getDomain(currentUrl);
        pwaInfoOutput.innerHTML = `
            <div class="info-card">
                <h4>🌐 URL Activa</h4>
                <p>${escapeHtml(currentUrl)}</p>
            </div>
            <div class="info-card">
                <h4>📱 Manifiesto PWA Simulado</h4>
                <p><strong>Nombre:</strong> ${escapeHtml(domain)}</p>
                <p><strong>Display:</strong> standalone</p>
                <p><strong>Orientación:</strong> any</p>
                <p><strong>Theme Color:</strong> #1A1A1A</p>
                <p><strong>Background:</strong> #0D0D0D</p>
                <p><strong>Scope:</strong> ${escapeHtml(window.location.origin)}</p>
            </div>
            <div class="info-card">
                <h4>⚡ Entorno</h4>
                <p><strong>Motor:</strong> ${window.Capacitor ? 'Capacitor Android Nativo' : 'Navegador Web / PWA'}</p>
                <p><strong>Plataforma:</strong> ${navigator.userAgent}</p>
            </div>
        `;
    }

    // Open in standalone popup window
    function openInStandaloneWindow(url) {
        const width = 1024;
        const height = 768;
        const left = Math.max(0, (window.screen.width - width) / 2);
        const top = Math.max(0, (window.screen.height - height) / 2);

        const features = `popup=yes,width=${width},height=${height},top=${top},left=${left},menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes`;
        appendLog('info', `Abriendo ventana PWA independiente: ${url}`);
        return window.open(url, '_blank', features);
    }

    // Instalar PWA / Crear acceso directo
    async function installPwa(url) {
        appendLog('info', `Iniciando solicitud de instalación para: ${url}`);

        if (deferredPrompt) {
            try {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                appendLog('info', `Resultado de instalación PWA: ${outcome}`);
                if (outcome === 'accepted') {
                    deferredPrompt = null;
                }
                return;
            } catch (err) {
                console.warn('[Install] Error al usar deferredPrompt:', err);
            }
        }

        // Generar archivo webmanifest dinámico descargable o instrucciones
        const domain = getDomain(url);
        const manifestData = {
            name: domain,
            short_name: domain.slice(0, 12),
            start_url: url,
            display: "standalone",
            background_color: "#0D0D0D",
            theme_color: "#1A1A1A",
            icons: [
                {
                    src: `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
                    sizes: "128x128",
                    type: "image/png"
                }
            ]
        };

        const blob = new Blob([JSON.stringify(manifestData, null, 2)], { type: 'application/json' });
        const manifestUrl = URL.createObjectURL(blob);

        const confirmInstall = confirm(
            `¿Deseas instalar "${domain}" como aplicación PWA?\n\n` +
            `• En Android / Chrome: Abre el menú del navegador ⋮ y selecciona "Agregar a la pantalla principal" o "Instalar aplicación".\n` +
            `• En PC: Haz clic en el ícono de instalación en la barra de direcciones o usa ventana PWA.`
        );

        if (confirmInstall) {
            openInStandaloneWindow(url);
        }
    }

    // Helper Functions
    function formatUrl(url) {
        let trimmed = url.trim();
        if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
            trimmed = 'https://' + trimmed;
        }
        return trimmed;
    }

    function getDomain(url) {
        try {
            return new URL(url).hostname;
        } catch {
            return url;
        }
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
        history = history.filter(item => item !== url);
        history.unshift(url);
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
                <div class="history-actions">
                    <button class="btn-icon install-btn" title="Instalar como PWA">📥</button>
                    <button class="btn-icon delete-btn" title="Eliminar">🗑</button>
                </div>
            `;

            // Click item to open
            item.addEventListener('click', (e) => {
                if (e.target.closest('.delete-btn') || e.target.closest('.install-btn')) return;
                urlInput.value = url;
                openUrl(url);
            });

            // Click install button
            const installBtn = item.querySelector('.install-btn');
            installBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                installPwa(url);
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
        currentUrl = url;
        appendLog('info', `Cargando sitio web: ${url}`);

        // 1. Capacitor Nativo (Android/iOS)
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Browser) {
            window.Capacitor.Plugins.Browser.open({ url: url });
            return;
        } else if (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) {
            window.open(url, '_system');
            return;
        }

        // 2. Modo Web / Vercel:
        const popup = openInStandaloneWindow(url);

        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
            viewerTitle.textContent = url;
            pwaIframe.src = url;
            pwaViewer.classList.remove('hidden');
            appendLog('info', 'Sitio abierto en el visor embebido con controles PWA');
        }
    }

    function escapeHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // ==========================================
    // Animación de Red Neuronal (Canvas)
    // ==========================================
    function initNeuralNetworkCanvas() {
        const canvas = document.getElementById('neuralCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            initNodes();
        });

        const nodeCount = Math.floor(Math.min(width, height) / 18);
        const maxDistance = 120;
        let nodes = [];

        class Node {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.vx = (Math.random() - 0.5) * 0.7;
                this.vy = (Math.random() - 0.5) * 0.7;
                this.radius = Math.random() * 1.8 + 1.2;
                this.pulseSpeed = 0.02 + Math.random() * 0.02;
                this.pulse = Math.random() * Math.PI;
            }

            update() {
                this.x += this.vx;
                this.y += this.vy;
                this.pulse += this.pulseSpeed;

                if (this.x < 0 || this.x > width) this.vx *= -1;
                if (this.y < 0 || this.y > height) this.vy *= -1;
            }

            draw() {
                const currentRadius = this.radius + Math.sin(this.pulse) * 0.6;
                ctx.beginPath();
                ctx.arc(this.x, this.y, Math.max(0.5, currentRadius), 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(96, 165, 250, 0.75)';
                ctx.shadowColor = 'rgba(59, 130, 246, 0.8)';
                ctx.shadowBlur = 8;
                ctx.fill();
            }
        }

        function initNodes() {
            nodes = [];
            const count = Math.min(65, Math.floor((width * height) / 16000));
            for (let i = 0; i < count; i++) {
                nodes.push(new Node());
            }
        }

        initNodes();

        function animate() {
            ctx.clearRect(0, 0, width, height);
            ctx.shadowBlur = 0;

            // Draw connections
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < maxDistance) {
                        const alpha = (1 - dist / maxDistance) * 0.35;
                        ctx.beginPath();
                        ctx.moveTo(nodes[i].x, nodes[i].y);
                        ctx.lineTo(nodes[j].x, nodes[j].y);
                        ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                }
            }

            // Update & draw nodes
            for (let i = 0; i < nodes.length; i++) {
                nodes[i].update();
                nodes[i].draw();
            }

            requestAnimationFrame(animate);
        }

        animate();
    }
});
