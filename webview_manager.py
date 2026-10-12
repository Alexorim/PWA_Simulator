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
from config import WEBVIEW_WIDTH, WEBVIEW_HEIGHT, PROFILE_DIR

def _launch_process(config_data: Dict[str, Any], on_close: Optional[Callable] = None):
    """Ejecuta pwa_runner en un subproceso independiente con la configuración dada."""
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
            print(f"Error al iniciar subproceso: {e}")
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

def open_as_pwa(url: str, manifest: Dict[str, Any], icon_path: Optional[str] = None, on_close: Optional[Callable] = None):
    """
    Abre la URL configurada como PWA en un subproceso independiente con perfil persistente compartido.
    """
    title = manifest.get('name') or manifest.get('short_name') or 'PWA'
    bg_color = manifest.get('background_color', '#0D0D0D')

    config_data = {
        "url": url,
        "title": title,
        "background_color": bg_color,
        "width": WEBVIEW_WIDTH,
        "height": WEBVIEW_HEIGHT,
        "icon_path": icon_path,
        "storage_path": PROFILE_DIR,
        "is_pwa": True
    }
    _launch_process(config_data, on_close)

def open_google_login(on_close: Optional[Callable] = None):
    """
    Abre la ventana dedicada para inicio de sesión en Google con el perfil persistente compartido.
    """
    config_data = {
        "url": "https://accounts.google.com/ServiceLogin?hl=es",
        "title": "Iniciar sesión con Google — PWA Simulator",
        "background_color": "#FFFFFF",
        "width": 620,
        "height": 720,
        "icon_path": None,
        "storage_path": PROFILE_DIR,
        "is_pwa": False
    }
    _launch_process(config_data, on_close)

def open_google_logout(on_close: Optional[Callable] = None):
    """
    Cierra SOLO la sesión de Google usando su propio endpoint de logout dentro del perfil
    compartido (las demás sesiones: ChatGPT, Discord, WhatsApp... se conservan).
    """
    config_data = {
        "url": "https://accounts.google.com/Logout?hl=es",
        "title": "Cerrar sesión de Google — PWA Simulator",
        "background_color": "#FFFFFF",
        "width": 620,
        "height": 720,
        "icon_path": None,
        "storage_path": PROFILE_DIR,
        "is_pwa": False
    }
    _launch_process(config_data, on_close)
