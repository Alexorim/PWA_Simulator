"""
webview_manager.py - Gestor de ventanas PWA ejecutadas en subprocesos independientes
"""
import os
import sys
import json
import tempfile
import threading
import subprocess
from typing import Optional, Callable, Dict, Any
from config import WEBVIEW_WIDTH, WEBVIEW_HEIGHT

def open_as_pwa(url: str, manifest: Dict[str, Any], icon_path: Optional[str] = None, on_close: Optional[Callable] = None):
    """
    Abre la URL configurada como PWA en un subproceso independiente.
    Garantiza que pywebview se ejecute en su propio hilo principal sin interferir con CustomTkinter.
    """
    title = manifest.get('name') or manifest.get('short_name') or 'PWA'
    bg_color = manifest.get('background_color', '#0D0D0D')

    # Preparar archivo de configuración temporal
    config_data = {
        "url": url,
        "title": title,
        "background_color": bg_color,
        "width": WEBVIEW_WIDTH,
        "height": WEBVIEW_HEIGHT,
        "icon_path": icon_path
    }

    temp_fd, config_path = tempfile.mkstemp(prefix="pwa_cfg_", suffix=".json")
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
    except Exception as e:
        print(f"Error al escribir configuración temporal: {e}")
        if on_close:
            on_close()
        return

    # Determinar el comando a ejecutar
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        cmd = [sys.executable, "--pwa-runner", config_path]
    else:
        runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pwa_runner.py")
        cmd = [sys.executable, runner_path, config_path]

    def _monitor_process():
        try:
            # Crear proceso independiente
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            proc.wait()
        except Exception as e:
            print(f"Error al iniciar subproceso PWA: {e}")
        finally:
            # Limpiar archivo de configuración si aún existe
            if os.path.exists(config_path):
                try:
                    os.remove(config_path)
                except Exception:
                    pass
            if on_close:
                on_close()

    monitor_thread = threading.Thread(target=_monitor_process, daemon=True)
    monitor_thread.start()
