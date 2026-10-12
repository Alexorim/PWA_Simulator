"""
atomic_io.py - Escritura atómica de archivos JSON (tmp -> flush/fsync -> replace).
Evita archivos truncados/corruptos si la aplicación se cierra durante una escritura.
"""
import os
import json
import time
import tempfile
from typing import Any


def write_json_atomic(path: str, data: Any, *, indent: int = 4, ensure_ascii: bool = True) -> None:
    """Escribe `data` como JSON en `path` de forma atómica. Lanza OSError si falla."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())

        # En Windows, os.replace puede fallar si otro proceso (antivirus, otra instancia)
        # tiene el destino abierto momentáneamente: reintentos cortos.
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
