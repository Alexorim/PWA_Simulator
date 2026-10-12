"""
google_auth.py - Indicador de sesión Google para la UI del lanzador.

IMPORTANTE: este módulo es SOLO informativo. La persistencia real de sesiones (Google, ChatGPT,
Discord, etc.) la gestiona WebView2 en el perfil persistente (config.PROFILE_DIR); nada aquí
lee valores de cookies, tokens ni contraseñas (solo nombres/expiración de cookies, en una copia).
"""
import os
import time
import shutil
import sqlite3
import tempfile
from typing import Optional, Tuple
from config import PROFILE_DIR

# Segundos entre 1601-01-01 (epoch de Chromium) y 1970-01-01
_CHROMIUM_EPOCH_OFFSET = 11644473600

def is_google_logged_in() -> Optional[bool]:
    """
    Heurística best-effort sobre la BD de cookies de Chromium (detalle interno de WebView2).
    Devuelve True/False, o None si no se puede verificar (p. ej. WebView2 mantiene la BD
    bloqueada mientras hay una PWA abierta). None NO significa "sin sesión".
    """
    cookie_candidates = [
        os.path.join(PROFILE_DIR, "EBWebView", "Default", "Network", "Cookies"),
        os.path.join(PROFILE_DIR, "EBWebView", "Default", "Cookies"),
    ]

    cookie_file = None
    for candidate in cookie_candidates:
        if os.path.exists(candidate):
            cookie_file = candidate
            break

    if not cookie_file:
        return False

    temp_copy = None
    try:
        # Copiar a temporal para evitar problemas de bloqueo de archivo por parte de WebView2
        temp_fd, temp_copy = tempfile.mkstemp(prefix="g_chk_", suffix=".db")
        os.close(temp_fd)
        try:
            shutil.copy2(cookie_file, temp_copy)
        except OSError:
            return None  # BD bloqueada por WebView2: estado desconocido

        conn = sqlite3.connect(temp_copy, timeout=2.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
            if not cursor.fetchone():
                return False

            columns = {row[1] for row in cursor.execute("PRAGMA table_info(cookies)")}

            # Cookies críticas que confirman una sesión de cuenta Google (host exacto o subdominio)
            query = """
                SELECT COUNT(*) FROM cookies
                WHERE (host_key = 'google.com' OR host_key LIKE '%.google.com')
                AND name IN ('SID', 'SSID', 'HSID', 'SAPISID', 'APISID', 'ACCOUNT_CHOOSER', '__Secure-1PSID')
            """
            params: tuple = ()
            if "expires_utc" in columns:
                # Ignorar cookies ya expiradas que Chromium aún no ha purgado (0 = cookie de sesión)
                now_chromium = int((time.time() + _CHROMIUM_EPOCH_OFFSET) * 1_000_000)
                query += " AND (expires_utc = 0 OR expires_utc > ?)"
                params = (now_chromium,)

            cursor.execute(query, params)
            row = cursor.fetchone()
        finally:
            conn.close()

        count = row[0] if row else 0
        return count > 0
    except Exception:
        return None
    finally:
        if temp_copy and os.path.exists(temp_copy):
            try:
                os.remove(temp_copy)
            except Exception:
                pass

def clear_browser_profile() -> Tuple[bool, str]:
    """
    Borra TODO el perfil WebView2 (cookies, LocalStorage, IndexedDB, caché) de TODOS los sitios.

    Primero renombra la carpeta: en Windows el rename falla si WebView2 tiene archivos abiertos,
    lo que detecta de forma fiable que hay PWAs en uso y evita un borrado parcial que corrompa
    el perfil (el anterior rmtree(ignore_errors=True) podía dejarlo a medias).
    """
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR, exist_ok=True)
        return True, "El perfil ya estaba vacío."

    trash_dir = f"{PROFILE_DIR}.deleting-{int(time.time())}"
    try:
        os.rename(PROFILE_DIR, trash_dir)
    except OSError:
        return False, "Cierra todas las ventanas PWA antes de borrar los datos de navegación."

    os.makedirs(PROFILE_DIR, exist_ok=True)
    shutil.rmtree(trash_dir, ignore_errors=True)
    return True, "Datos de navegación borrados."
