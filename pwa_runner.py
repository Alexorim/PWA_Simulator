"""
pwa_runner.py - Ejecutor de ventana PWA independiente usando pywebview y Edge WebView2
"""
import sys
import os
import json
import webview
from typing import Optional, Dict, Any

# Inyección JS para emular entorno PWA nativo y atajos de teclado
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

    // 3. Ocultar banners de 'Descarga la app en Android/iOS' frecuentes
    const hideBannersStyle = document.createElement('style');
    hideBannersStyle.innerHTML = `
        .smartbanner,
        .app-banner,
        .install-app-banner,
        .mobile-web-banner,
        [aria-label*="Install app" i],
        [data-testid*="app-upsell" i],
        [id*="smartbanner" i] {
            display: none !important;
        }
        /* Scrollbars oscuras y discretas */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #121212;
        }
        ::-webkit-scrollbar-thumb {
            background: #333333;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #4F46E5;
        }
    `;
    if (document.head) {
        document.head.appendChild(hideBannersStyle);
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            document.head.appendChild(hideBannersStyle);
        });
    }

    // 4. Soporte para atajos de teclado esenciales:
    // F5 o Ctrl+R: Recargar
    // Alt + Flecha Izquierda: Atrás
    // Alt + Flecha Derecha: Adelante
    window.addEventListener('keydown', function(e) {
        if (e.key === 'F5' || (e.ctrlKey && (e.key === 'r' || e.key === 'R'))) {
            e.preventDefault();
            window.location.reload();
        } else if (e.altKey && e.key === 'ArrowLeft') {
            e.preventDefault();
            window.history.back();
        } else if (e.altKey && e.key === 'ArrowRight') {
            e.preventDefault();
            window.history.forward();
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

        # Iniciar WebView usando el runtime nativo de Edge WebView2
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

        # Eliminar archivo temporal si es posible
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
