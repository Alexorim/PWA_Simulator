import json
import os
import threading
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Any
from datetime import datetime, timezone
from urllib.parse import urlparse
from config import HISTORY_FILE, MAX_HISTORY
from atomic_io import write_json_atomic

# Serializa lecturas/escrituras dentro del proceso (worker de detección + hilo UI)
_lock = threading.RLock()

@dataclass
class HistoryEntry:
    url: str
    title: str
    favicon_path: Optional[str]
    timestamp: str

def _url_key(url: str) -> str:
    """Clave de deduplicación: esquema/host en minúsculas y sin '/' final (no altera la URL guardada)."""
    try:
        p = urlparse(url.strip())
        key = f"{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip('/')}"
        return key + (f"?{p.query}" if p.query else "")
    except Exception:
        return url.strip()

def _backup_corrupt_file() -> None:
    """Conserva el archivo dañado en lugar de sobrescribirlo (permite recuperación manual)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(HISTORY_FILE, f"{HISTORY_FILE}.corrupt-{stamp}")
    except OSError:
        pass

def _load_raw() -> Tuple[List[Any], bool]:
    """Devuelve (datos, ok). ok=False indica error de E/S: los mutadores NO deben sobrescribir."""
    if not os.path.exists(HISTORY_FILE):
        return [], True
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        _backup_corrupt_file()
        return [], True
    except OSError:
        return [], False
    if not isinstance(data, list):
        _backup_corrupt_file()
        return [], True
    return data, True

def _parse_entries(data: List[Any]) -> List[HistoryEntry]:
    """Parseo tolerante: descarta elementos inválidos individualmente y deduplica."""
    entries: List[HistoryEntry] = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        key = _url_key(url)
        if key in seen:
            continue
        seen.add(key)
        entries.append(HistoryEntry(
            url=url,
            title=str(item.get("title") or ""),
            favicon_path=item.get("favicon_path") or None,
            timestamp=str(item.get("timestamp") or ""),
        ))
    return entries

def get_history() -> List[HistoryEntry]:
    with _lock:
        data, _ = _load_raw()
        return _parse_entries(data)

def _save_history(history: List[HistoryEntry]) -> bool:
    try:
        write_json_atomic(HISTORY_FILE, [asdict(entry) for entry in history], indent=4)
        return True
    except OSError:
        return False

def add_entry(url: str, title: str, favicon_path: Optional[str] = None):
    with _lock:
        data, ok = _load_raw()
        if not ok:
            return  # No sobrescribir un historial que no se pudo leer
        key = _url_key(url)
        history = [entry for entry in _parse_entries(data) if _url_key(entry.url) != key]

        new_entry = HistoryEntry(
            url=url,
            title=title,
            favicon_path=favicon_path,
            # Mismo formato ISO sin zona que antes (evita datetime.utcnow(), obsoleto en 3.12)
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        )
        history.insert(0, new_entry)
        _save_history(history[:MAX_HISTORY])

def clear_history():
    with _lock:
        _save_history([])

def remove_entry(url: str):
    with _lock:
        data, ok = _load_raw()
        if not ok:
            return
        key = _url_key(url)
        _save_history([entry for entry in _parse_entries(data) if _url_key(entry.url) != key])
