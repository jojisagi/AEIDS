# model/repositories/base.py
from __future__ import annotations
from typing import Protocol, Any, Iterable, Sequence, Mapping

class DBLike(Protocol):
    """Abstracción mínima de tu OracleDB."""
    def get_connection(self) -> Any: ...

def fetchall_dict(cursor) -> list[dict]:
    """Convierte cursor.fetchall() a lista de dicts (nombre_columna->valor)."""
    rows = cursor.fetchall() or []
    cols = [c[0].lower() for c in cursor.description] if cursor.description else []
    out: list[dict] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
        elif isinstance(r, Sequence):
            out.append({cols[i]: r[i] for i in range(min(len(cols), len(r)))})
        else:
            out.append({"value": r})
    return out