"""
quick_access.py - Gestor de accesos directos y enlaces rápidos en formato JSON dentro de URLS/
Guarda cada sitio web configurado con su metadata JSON y descarga su icono directamente en la carpeta URLS/.
"""
import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any, Tuple

from config import URLS_DIR, HISTORY_FILE, BASE_DIR
from favicon_extractor import favicon_fallback
from atomic_io import write_json_atomic

def _slugify(text: str) -> str:
    """Genera un identificador limpio y seguro para archivos."""
    clean = re.sub(r'https?://', '', text)
    clean = re.sub(r'www\.', '', clean)
    clean = clean.split('/')[0] # Quedarse con el dominio base
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    clean = clean.replace('.', '_')
    return clean.strip('_').lower() or "shortcut"

def save_quick_access(url: str, title: str, icon_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Registra un acceso rápido guardando:
    1. El icono descargado en URLS/<slug>.ico
    2. El archivo JSON individual URLS/<slug>.json
    3. Actualiza el índice consolidado URLS/shortcuts.json
    """
    os.makedirs(URLS_DIR, exist_ok=True)
    
    parsed = urlparse(url)
    domain = parsed.netloc or url.split('/')[0]
    slug = _slugify(domain or url)

    # 1. Gestionar y persistir el icono directamente en URLS/
    dest_icon_name = f"{slug}.ico"
    dest_icon_path = os.path.join(URLS_DIR, dest_icon_name)
    saved_icon_path = None

    if icon_path and os.path.exists(icon_path):
        try:
            shutil.copy2(icon_path, dest_icon_path)
            saved_icon_path = dest_icon_path
        except Exception:
            pass
    elif not os.path.exists(dest_icon_path):
        # Si no vino icono o no existe en destino, descargar usando fallback
        try:
            downloaded_temp = favicon_fallback(domain or url)
            if downloaded_temp and os.path.exists(downloaded_temp):
                shutil.copy2(downloaded_temp, dest_icon_path)
                saved_icon_path = dest_icon_path
        except Exception:
            pass
    else:
        saved_icon_path = dest_icon_path

    # 2. Generar metadata del acceso directo
    shortcut_data = {
        "title": title or domain or url,
        "url": url,
        "domain": domain,
        "icon_file": dest_icon_name if saved_icon_path and os.path.exists(saved_icon_path) else None,
        "icon_path": saved_icon_path if saved_icon_path and os.path.exists(saved_icon_path) else None,
        "updated_at": datetime.utcnow().isoformat()
    }

    # 3. Guardar archivo JSON individual
    json_file_path = os.path.join(URLS_DIR, f"{slug}.json")
    try:
        write_json_atomic(json_file_path, shortcut_data, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar acceso directo en {json_file_path}: {e}")

    # 4. Actualizar archivo consolidado URLS/shortcuts.json
    _update_consolidated_index(shortcut_data)

    return shortcut_data

def _update_consolidated_index(new_entry: Dict[str, Any]):
    """Mantiene sincronizado el archivo consolidado URLS/shortcuts.json."""
    index_file = os.path.join(URLS_DIR, "shortcuts.json")
    items = []
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                items = json.load(f)
                if not isinstance(items, list):
                    items = []
        except Exception:
            items = []

    # Reemplazar o insertar al inicio
    items = [it for it in items if it.get("url") != new_entry.get("url")]
    items.insert(0, new_entry)

    try:
        write_json_atomic(index_file, items, indent=4, ensure_ascii=False)
    except Exception:
        pass

def sync_existing_history():
    """
    Migra y genera los archivos JSON y descarga iconos para todas las páginas que ya existían en history.json.
    """
    if not os.path.exists(HISTORY_FILE):
        return

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

        if isinstance(history, list):
            for entry in history:
                url = entry.get('url')
                title = entry.get('title')
                icon_path = entry.get('favicon_path')
                if url:
                    save_quick_access(url, title, icon_path)
    except Exception as e:
        print(f"Error al sincronizar historial existente a URLS/: {e}")

# ---------------------------------------------------------------------------
# Acceso directo .lnk en el Escritorio (Windows Script Host / WScript.Shell)
# ---------------------------------------------------------------------------
# Script VBS ESTÁTICO: los datos (URL, rutas, título) llegan por WScript.Arguments y nunca se
# interpolan como código. Antes la URL se insertaba dentro del VBS: una URL con comillas podía
# romper el script o inyectar VBScript arbitrario.
# SpecialFolders("Desktop") resuelve el escritorio real (incluido OneDrive).
_SHORTCUT_VBS = r'''
Set args = WScript.Arguments
If args.Count < 6 Then WScript.Quit 2
Set oWS = CreateObject("WScript.Shell")
sDesk = oWS.SpecialFolders("Desktop")
If sDesk = "" Then sDesk = oWS.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop"
Set oLink = oWS.CreateShortcut(sDesk & "\" & args(0) & ".lnk")
oLink.TargetPath = args(1)
sArgs = ""
If args(2) <> "-" Then sArgs = Chr(34) & args(2) & Chr(34) & " "
oLink.Arguments = sArgs & Chr(34) & args(5) & Chr(34)
oLink.WorkingDirectory = args(3)
If args(4) <> "-" Then oLink.IconLocation = args(4)
oLink.Description = "PWA - " & args(0)
oLink.WindowStyle = 1
oLink.Save
'''

def _shortcut_launch_spec() -> Tuple[str, str, str, str]:
    """(target, script_arg|'-', working_dir, icon_location|'-') según modo script o .exe."""
    if getattr(sys, 'frozen', False):
        # En el .exe no existe main.py: el propio ejecutable recibe la URL como argv[1]
        exe = sys.executable
        return exe, "-", os.path.dirname(exe), f"{exe},0"

    python_exe = sys.executable
    # Preferir pythonw.exe para no abrir una consola negra junto a la PWA
    if os.path.basename(python_exe).lower() == "python.exe":
        pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        if os.path.exists(pythonw):
            python_exe = pythonw
    main_py = os.path.join(BASE_DIR, "main.py")
    icon_path = os.path.join(BASE_DIR, "icon.ico")
    icon_loc = f"{icon_path},0" if os.path.exists(icon_path) else "-"
    return python_exe, main_py, BASE_DIR, icon_loc

def create_desktop_shortcut(url: str, title: Optional[str]) -> Tuple[bool, str, str]:
    """
    Crea un .lnk en el Escritorio que abre la URL como PWA independiente.
    Devuelve (ok, nombre_del_lnk, mensaje_error).
    """
    if urlparse(url or "").scheme.lower() not in ("http", "https"):
        return False, "", "Solo se admiten URLs http/https."
    safe_url = url.replace('"', '%22')

    clean_title = "".join(c for c in (title or urlparse(url).netloc) if c.isalnum() or c in (' ', '_', '-')).strip()
    if not clean_title:
        clean_title = "PWA"

    target, script_arg, work_dir, icon_loc = _shortcut_launch_spec()

    fd, temp_vbs = tempfile.mkstemp(prefix="create_pwa_", suffix=".vbs")
    try:
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(_SHORTCUT_VBS.strip())

        result = subprocess.run(
            ["cscript", "//Nologo", temp_vbs, clean_title, target, script_arg, work_dir, icon_loc, safe_url],
            capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return True, f"{clean_title}.lnk", ""
        return False, f"{clean_title}.lnk", (result.stderr or result.stdout or f"cscript código {result.returncode}").strip()
    except Exception as e:
        return False, f"{clean_title}.lnk", str(e)
    finally:
        try:
            os.remove(temp_vbs)
        except OSError:
            pass
