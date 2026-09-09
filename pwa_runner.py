"""
pwa_runner.py - Ejecutor de ventana PWA independiente usando pywebview y Edge WebView2
Incluye menú flotante (Recargar, Instalar, Herramientas Dev, Cerrar) y atajos de teclado
"""
import sys
import os
import json
import webview
from typing import Optional, Dict, Any

# Inyección JS para entorno PWA nativo, menú flotante de controles y DevTools
PWA_INJECTION_SCRIPT = """
(function() {
    // 1. Simular navigator.standalone para Safari/WebKit y display-mode
    try {
        Object.defineProperty(navigator, 'standalone', {
            get: () => true,
            configurable: true
        });
    } catch(e) {}

    // 2. Simular matchMedia para '(display-mode: standalone)'
    try {
        const originalMatchMedia = window.matchMedia;
        window.matchMedia = function(query) {
            if (query && (query.includes('display-mode: standalone') || query.includes('display-mode: standalone-app'))) {
                return {
                    matches: true,
                    media: query,
                    onchange: null,
                    addListener: function() {},
                    removeListener: function() {},
                    addEventListener: function() {},
                    removeEventListener: function() {},
                    dispatchEvent: function() { return false; }
                };
            }
            return originalMatchMedia.apply(this, arguments);
        };
    } catch(e) {}

    // 3. Estilos y Menú flotante PWA
    const style = document.createElement('style');
    style.innerHTML = `
        .smartbanner, .app-banner, .install-app-banner, .mobile-web-banner,
        [aria-label*="Install app" i], [data-testid*="app-upsell" i], [id*="smartbanner" i] {
            display: none !important;
        }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #121212; }
        ::-webkit-scrollbar-thumb { background: #333333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3B82F6; }

        /* Botón flotante PWA Menu */
        #pwa-floating-menu-btn {
            position: fixed;
            top: 14px;
            right: 14px;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(24, 24, 27, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #FFFFFF;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 2147483645;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
            user-select: none;
            transition: transform 0.2s, background 0.2s, opacity 0.3s;
            opacity: 0.6;
        }
        #pwa-floating-menu-btn:hover {
            opacity: 1;
            transform: scale(1.08);
            background: rgba(39, 39, 42, 0.95);
        }

        /* Panel desplegable PWA */
        #pwa-floating-dropdown {
            position: fixed;
            top: 56px;
            right: 14px;
            background: rgba(18, 18, 20, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.85);
            padding: 6px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            min-width: 220px;
            z-index: 2147483646;
            backdrop-filter: blur(16px);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .pwa-menu-item {
            background: none;
            border: none;
            color: #E4E4E7;
            font-size: 13px;
            padding: 9px 12px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            text-align: left;
            transition: background 0.15s, color 0.15s;
            width: 100%;
        }
        .pwa-menu-item:hover {
            background: rgba(255, 255, 255, 0.08);
            color: #FFFFFF;
        }
        .pwa-menu-item.danger {
            color: #F87171;
        }
        .pwa-menu-item.danger:hover {
            background: rgba(239, 68, 68, 0.16);
        }
        .pwa-menu-divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 4px 0;
        }

        /* Mini DevTools Drawer */
        #pwa-devtools-drawer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 48%;
            background: #09090B;
            border-top: 1px solid #27272A;
            z-index: 2147483647;
            display: flex;
            flex-direction: column;
            font-family: 'Consolas', 'Courier New', monospace;
            box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.85);
        }
        .pwa-dt-header {
            background: #18181B;
            border-bottom: 1px solid #27272A;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 12px;
        }
        .pwa-dt-tabs { display: flex; gap: 6px; }
        .pwa-dt-tab {
            background: none;
            border: none;
            color: #A1A1AA;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
        }
        .pwa-dt-tab.active {
            background: #27272A;
            color: #FFFFFF;
            font-weight: bold;
        }
        .pwa-dt-body {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            font-size: 12px;
            color: #D4D4D8;
        }
        .pwa-log-line {
            padding: 3px 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            word-break: break-all;
        }
    `;

    function injectUI() {
        if (document.getElementById('pwa-floating-menu-btn')) return;

        document.head.appendChild(style);

        // Crear botón flotante
        const btn = document.createElement('div');
        btn.id = 'pwa-floating-menu-btn';
        btn.title = 'Menú PWA Simulator';
        btn.innerHTML = '⋮';
        document.body.appendChild(btn);

        // Crear menú desplegable
        const dropdown = document.createElement('div');
        dropdown.id = 'pwa-floating-dropdown';
        dropdown.style.display = 'none';
        dropdown.innerHTML = `
            <button class="pwa-menu-item" id="pwa-act-reload">
                <span>🔄</span> Recargar página
            </button>
            <button class="pwa-menu-item" id="pwa-act-install">
                <span>📥</span> Instalar / Acceso directo
            </button>
            <button class="pwa-menu-item" id="pwa-act-devtools">
                <span>🛠</span> Herramientas Dev (DOM/Logs)
            </button>
            <div class="pwa-menu-divider"></div>
            <button class="pwa-menu-item danger" id="pwa-act-close">
                <span>✕</span> Cerrar ventana PWA
            </button>
        `;
        document.body.appendChild(dropdown);

        // Crear DevTools Drawer
        const devtools = document.createElement('div');
        devtools.id = 'pwa-devtools-drawer';
        devtools.style.display = 'none';
        devtools.innerHTML = `
            <div class="pwa-dt-header">
                <div class="pwa-dt-tabs">
                    <button class="pwa-dt-tab active" id="pwa-tab-console">Consola</button>
                    <button class="pwa-dt-tab" id="pwa-tab-dom">Estructura DOM</button>
                </div>
                <button style="background:none;border:none;color:#FFF;cursor:pointer;font-size:14px;" id="pwa-dt-close">✕</button>
            </div>
            <div class="pwa-dt-body" id="pwa-dt-content"></div>
        `;
        document.body.appendChild(devtools);

        // Eventos
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === 'none' ? 'flex' : 'none';
        });

        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && e.target !== btn) {
                dropdown.style.display = 'none';
            }
        });

        document.getElementById('pwa-act-reload').addEventListener('click', () => {
            dropdown.style.display = 'none';
            window.location.reload();
        });

        document.getElementById('pwa-act-install').addEventListener('click', () => {
            dropdown.style.display = 'none';
            alert('Para instalar este sitio como PWA en Windows:\n• Puedes crear un acceso directo desde PWA Simulator.\n• O si abres en Chrome/Edge, pulsa el botón (+) en la barra de direcciones.');
        });

        const dtContent = document.getElementById('pwa-dt-content');
        const dtTabConsole = document.getElementById('pwa-tab-console');
        const dtTabDom = document.getElementById('pwa-tab-dom');

        document.getElementById('pwa-act-devtools').addEventListener('click', () => {
            dropdown.style.display = 'none';
            devtools.style.display = 'flex';
            showConsoleLogs();
        });

        document.getElementById('pwa-dt-close').addEventListener('click', () => {
            devtools.style.display = 'none';
        });

        dtTabConsole.addEventListener('click', () => {
            dtTabConsole.classList.add('active');
            dtTabDom.classList.remove('active');
            showConsoleLogs();
        });

        dtTabDom.addEventListener('click', () => {
            dtTabDom.classList.add('active');
            dtTabConsole.classList.remove('active');
            showDomTree();
        });

        function showConsoleLogs() {
            dtContent.innerHTML = window.__pwa_logs.length === 0
                ? '<div style="color:#71717A;padding:8px;">No hay logs registrados aún.</div>'
                : window.__pwa_logs.map(l => `<div class="pwa-log-line" style="color:${l.color}">[${l.time}] ${l.msg}</div>`).join('');
            dtContent.scrollTop = dtContent.scrollHeight;
        }

        function showDomTree() {
            const headInfo = `<!-- Titulo: ${document.title} -->\\n` +
                             `<!-- URL: ${window.location.href} -->\\n\\n` +
                             `<!-- Scripts (${document.scripts.length}): -->\\n` +
                             Array.from(document.scripts).map(s => s.src || '[script inline]').join('\\n') +
                             `\\n\\n<!-- Meta tags: -->\\n` +
                             Array.from(document.querySelectorAll('meta')).map(m => m.outerHTML).join('\\n');
            dtContent.innerHTML = `<pre style="white-space:pre-wrap;color:#93C5FD;">${escapeHtml(headInfo)}</pre>`;
        }

        function escapeHtml(s) {
            return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    }

    // Interceptar console.log/warn/error
    window.__pwa_logs = [];
    const _log = console.log, _warn = console.warn, _err = console.error;
    function addLog(type, color, args) {
        const time = new Date().toLocaleTimeString();
        const msg = Array.from(args).map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ');
        window.__pwa_logs.push({ type, color, time, msg });
        if (window.__pwa_logs.length > 150) window.__pwa_logs.shift();
    }
    console.log = function() { addLog('log', '#E4E4E7', arguments); _log.apply(console, arguments); };
    console.warn = function() { addLog('warn', '#FBBF24', arguments); _warn.apply(console, arguments); };
    console.error = function() { addLog('error', '#F87171', arguments); _err.apply(console, arguments); };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectUI);
    } else {
        injectUI();
    }

    // Atajos de teclado: F5 / Ctrl+R / F12 (DevTools)
    window.addEventListener('keydown', function(e) {
        if (e.key === 'F5' || (e.ctrlKey && (e.key === 'r' || e.key === 'R'))) {
            e.preventDefault();
            window.location.reload();
        } else if (e.key === 'F12') {
            e.preventDefault();
            const dt = document.getElementById('pwa-devtools-drawer');
            if (dt) dt.style.display = dt.style.display === 'none' ? 'flex' : 'none';
        }
    });
})();
"""

def run_pwa(url: str, title: str = "PWA", background_color: str = "#0D0D0D", width: int = 1024, height: int = 768):
    """Crea y ejecuta la ventana PWA en el hilo principal del proceso."""
    try:
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            resizable=True,
            frameless=False,
            easy_drag=False,
            text_select=True,
            confirm_close=False,
            background_color=background_color
        )

        def on_loaded():
            try:
                window.evaluate_js(PWA_INJECTION_SCRIPT)
            except Exception:
                pass

        window.events.loaded += on_loaded

        # Iniciar WebView con soporte para inspección y controles Edge Chromium
        webview.start(gui='edgechromium', debug=False)
    except Exception as e:
        print(f"Error al ejecutar PWA: {e}", file=sys.stderr)
        sys.exit(1)

def run_from_config_file(config_path: str):
    """Carga los parámetros desde un archivo JSON y ejecuta la PWA."""
    if not os.path.exists(config_path):
        print(f"Archivo de configuración no encontrado: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        url = data.get("url")
        title = data.get("title", "PWA")
        bg_color = data.get("background_color", "#0D0D0D")
        width = data.get("width", 1024)
        height = data.get("height", 768)

        try:
            os.remove(config_path)
        except Exception:
            pass

        run_pwa(url=url, title=title, background_color=bg_color, width=width, height=height)
    except Exception as e:
        print(f"Error al procesar configuración: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_from_config_file(sys.argv[1])
    else:
        print("Uso: python pwa_runner.py <config.json>", file=sys.stderr)
