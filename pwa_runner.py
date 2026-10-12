"""
pwa_runner.py - Ejecutor de ventana PWA independiente usando pywebview y Edge WebView2
Incluye menú flotante (Recargar, Instalar, Herramientas Dev, Cerrar) y atajos de teclado
"""
import sys
import os
import re
import json
import webview
from urllib.parse import urlparse
from typing import Optional, Dict, Any

# Inyección JS para entorno PWA nativo, menú flotante de controles y DevTools
PWA_INJECTION_SCRIPT = """
(function() {
    // Evitar doble inyección en el mismo documento (wrappers y listeners duplicados)
    if (window.__pwaSimInjected) return;
    window.__pwaSimInjected = true;

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

        /* Barra de navegación personalizada estilo macOS */
        #pwa-macos-titlebar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 38px;
            background: rgba(14, 16, 23, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 14px;
            z-index: 2147483640;
            user-select: none;
            -webkit-user-select: none;
            box-sizing: border-box;
            -webkit-app-region: drag;
        }

        /* Contenedor flexible de los 3 punticos en el extremo izquierdo */
        .macos-traffic-lights {
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 2147483642;
            -webkit-app-region: no-drag;
            cursor: default;
        }

        /* Círculos perfectos de 12px estilo macOS */
        .macos-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: none;
            outline: none;
            padding: 0;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            position: relative;
            transition: transform 0.12s ease, filter 0.15s ease;
            -webkit-app-region: no-drag;
            box-shadow: 0 0.5px 1px rgba(0, 0, 0, 0.35);
        }

        /* Colores exactos de macOS */
        .macos-close {
            background-color: #ff5f56;
            border: 1px solid #e0443e;
        }
        .macos-minimize {
            background-color: #ffbd2e;
            border: 1px solid #dea123;
        }
        .macos-maximize {
            background-color: #27c93f;
            border: 1px solid #1aab29;
        }

        /* Iconos interiores sutiles en hover */
        .macos-icon {
            font-size: 8px;
            font-weight: 800;
            line-height: 1;
            color: rgba(0, 0, 0, 0.65);
            opacity: 0;
            transition: opacity 0.12s ease;
            pointer-events: none;
        }

        .macos-traffic-lights:hover .macos-icon {
            opacity: 1;
        }
        .macos-dot:hover {
            filter: brightness(1.15);
        }
        .macos-dot:active {
            filter: brightness(0.85);
        }

        /* Título centrado en la barra */
        .pwa-macos-title {
            color: #94A3B8;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-weight: 500;
            letter-spacing: 0.3px;
            pointer-events: none;
            text-align: center;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 0 16px;
        }

        .pwa-macos-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            -webkit-app-region: no-drag;
            z-index: 2147483642;
        }

        .pwa-macos-menu-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #E2E8F0;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.15s, color 0.15s;
            -webkit-app-region: no-drag;
        }
        .pwa-macos-menu-btn:hover {
            background: rgba(255, 255, 255, 0.16);
            color: #FFFFFF;
        }

        /* Panel desplegable PWA */
        #pwa-floating-dropdown {
            position: fixed;
            top: 44px;
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
        if (document.getElementById('pwa-macos-titlebar')) return;

        document.head.appendChild(style);

        // 1. Crear barra de navegación personalizada estilo macOS
        const titlebar = document.createElement('div');
        titlebar.id = 'pwa-macos-titlebar';
        titlebar.className = 'pywebview-drag-region';
        titlebar.innerHTML = `
            <div class="macos-traffic-lights">
                <button class="macos-dot macos-close" id="macos-btn-close" title="Cerrar">
                    <span class="macos-icon">✕</span>
                </button>
                <button class="macos-dot macos-minimize" id="macos-btn-min" title="Minimizar">
                    <span class="macos-icon">−</span>
                </button>
                <button class="macos-dot macos-maximize" id="macos-btn-max" title="Maximizar / Restaurar">
                    <span class="macos-icon">+</span>
                </button>
            </div>
            <div class="pwa-macos-title pywebview-drag-region">${escapeHtml(document.title || 'PWA Simulator')}</div>
            <div class="pwa-macos-actions">
                <button class="pwa-macos-menu-btn" id="pwa-floating-menu-btn" title="Opciones de la PWA">⋮ Menú</button>
            </div>
        `;
        document.body.prepend(titlebar);

        // Desplazar el contenido del body para que la barra fija no tape nada
        try {
            document.body.style.marginTop = '38px';
        } catch(e) {}

        const btn = document.getElementById('pwa-floating-menu-btn');

        // 2. Crear menú desplegable
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

        // 3. Crear DevTools Drawer
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

        // 4. Interactividad de los 3 botones macOS (comunicación directa con Python API)
        const btnClose = document.getElementById('macos-btn-close');
        const btnMin = document.getElementById('macos-btn-min');
        const btnMax = document.getElementById('macos-btn-max');

        if (btnClose) {
            btnClose.addEventListener('click', (e) => {
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api && window.pywebview.api.close_window) {
                    window.pywebview.api.close_window();
                }
            });
        }

        if (btnMin) {
            btnMin.addEventListener('click', (e) => {
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize_window) {
                    window.pywebview.api.minimize_window();
                }
            });
        }

        if (btnMax) {
            btnMax.addEventListener('click', (e) => {
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_maximize) {
                    window.pywebview.api.toggle_maximize();
                }
            });
        }

        // Eventos del menú desplegable
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.style.display = dropdown.style.display === 'none' ? 'flex' : 'none';
            });
        }

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
                : window.__pwa_logs.map(l => `<div class="pwa-log-line" style="color:${l.color}">[${l.time}] ${escapeHtml(l.msg)}</div>`).join('');
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
        try {
            const time = new Date().toLocaleTimeString();
            const msg = Array.from(args).map(a => {
                if (typeof a !== 'object' || a === null) return String(a);
                try { return JSON.stringify(a); } catch (_) { return Object.prototype.toString.call(a); }
            }).join(' ');
            window.__pwa_logs.push({ type, color, time, msg });
            if (window.__pwa_logs.length > 150) window.__pwa_logs.shift();
        } catch (_) { /* nunca romper el console.* del sitio */ }
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

_HEX_COLOR_RE = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

def _normalize_hex_color(value: Any, default: str = "#0D0D0D") -> str:
    """
    pywebview exige '#RRGGBB'. Los manifests pueden traer '#fff', 'white' o 'rgb(...)':
    '#fff' rompe el parseo interno de WebView2 y los nombres/rgb() lanzan ValueError en
    create_window (la ventana nunca se abría). Se normaliza o se usa el color por defecto.
    """
    if isinstance(value, str):
        m = _HEX_COLOR_RE.match(value.strip())
        if m:
            h = m.group(1)
            if len(h) == 3:
                h = ''.join(c * 2 for c in h)
            return '#' + h.upper()
    return default

def _create_window_controls(window):
    """
    API nativa MÍNIMA expuesta a JavaScript (solo controles de la propia ventana).

    SEGURIDAD: NO usar `js_api=<objeto>`. pywebview resuelve el nombre recibido desde JS con
    getattr encadenado sin filtrar '_' (util.get_nested_attribute), por lo que cualquier página
    cargada podía alcanzar `_window.gui.os.system` => ejecución remota de comandos.
    Con `window.expose()` y sin js_api, solo se resuelven estos nombres exactos.
    """
    state = {"maximized": False}

    def close_window():
        """Cierra la ventana de la PWA (Botón Rojo macOS)."""
        window.destroy()

    def minimize_window():
        """Minimiza la ventana a la barra de tareas (Botón Amarillo macOS)."""
        window.minimize()

    def toggle_maximize():
        """Alterna entre maximizado y tamaño restaurado (Botón Verde macOS)."""
        if not state["maximized"]:
            window.maximize()
            state["maximized"] = True
        else:
            window.restore()
            state["maximized"] = False

    return close_window, minimize_window, toggle_maximize

def run_pwa(url: str, title: str = "PWA", background_color: str = "#0D0D0D", width: int = 1024, height: int = 768, storage_path: Optional[str] = None, is_pwa: bool = True):
    """Crea y ejecuta la ventana en el hilo principal del proceso compartiendo el perfil persistente."""
    try:
        from config import PROFILE_DIR, USER_AGENT

        # Solo contenido web remoto: nunca file://, javascript:, etc.
        if not isinstance(url, str) or urlparse(url).scheme.lower() not in ("http", "https"):
            raise ValueError(f"URL no permitida (solo http/https): {url!r}")
        background_color = _normalize_hex_color(background_color)

        # Evita que popups de login / OAuth se abran en el navegador externo
        # (pywebview 6.x los carga en la MISMA ventana; ver docs de auditoría)
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
        # Descargas: pywebview las cancela en silencio por defecto. Con True se muestra
        # el diálogo nativo "Guardar como" (el usuario decide destino).
        webview.settings['ALLOW_DOWNLOADS'] = True
        # Nunca cargamos archivos locales: no añadir --allow-file-access-from-files
        webview.settings['ALLOW_FILE_URLS'] = False

        # Flags optimizados para mínimo consumo de CPU/RAM (Modo Gaming):
        # Mantiene activas llamadas WebRTC (Discord), streaming y aceleración GPU sin cortes en segundo plano
        perf_args = [
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--process-per-site",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--disable-breakpad",
            "--disable-sync",
            "--no-pings",
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
            "--disk-cache-size=104857600",
            "--media-cache-size=52428800",
            "--disable-features=Translate,InterestFeedContentSuggestions,CalculateNativeWinOcclusion"
        ]
        curr_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (curr_args + " " + " ".join(perf_args)).strip()

        # Ventana con marco nativo de Windows (permite mover, maximizar y restaurar sin bugs en Discord)
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            resizable=True,
            frameless=False,
            easy_drag=True,
            text_select=True,
            confirm_close=False,
            background_color=background_color
        )
        # Mismos nombres que usa el JS inyectado: window.pywebview.api.<nombre>()
        window.expose(*_create_window_controls(window))

        if is_pwa:
            def on_loaded():
                try:
                    window.evaluate_js(PWA_INJECTION_SCRIPT)
                except Exception:
                    pass

            window.events.loaded += on_loaded

        # Iniciar WebView persistente para retener sesión de Google y cookies
        webview.start(
            gui='edgechromium',
            debug=False,
            private_mode=False,
            storage_path=storage_path or PROFILE_DIR,
            user_agent=USER_AGENT
        )
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
        storage_path = data.get("storage_path")
        is_pwa = data.get("is_pwa", True)

        try:
            os.remove(config_path)
        except Exception:
            pass

        run_pwa(url=url, title=title, background_color=bg_color, width=width, height=height, storage_path=storage_path, is_pwa=is_pwa)
    except Exception as e:
        print(f"Error al procesar configuración: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_from_config_file(sys.argv[1])
    else:
        print("Uso: python pwa_runner.py <config.json>", file=sys.stderr)
