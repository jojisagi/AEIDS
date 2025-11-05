from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

def _get(m: Mapping[str, Any], *names: str) -> Any:
    for n in names:
        if n in m: 
            return m[n]
        # busca insensible a mayúsculas
        for k in m.keys():
            if str(k).lower() == n.lower():
                return m[k]
    return None

@dataclass(slots=True)
class Nota:
    cve_nota: int | None
    cve_orden: int
    texto: str
    creado_en: datetime | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Nota":
        """
        Admite:
          - dict con claves diversas: cve_nota / cve_orden_nota, nota/texto/descripcion, creado_en/fecha_created/fecha
          - tupla en orden: (cve_nota?, cve_orden, texto, creado_en?)
        """
        if isinstance(row, Mapping):
            cve_nota  = _get(row, "cve_nota", "cve_orden_nota", "id_nota", "id")
            cve_orden = _get(row, "cve_orden", "orden", "id_orden")
            texto     = _get(row, "nota", "texto", "descripcion")
            creado_en = _get(row, "creado_en", "fecha", "created_at", "fecha_creacion")
        else:
            # tupla/lista
            # intenta mapear heurísticamente
            # (cve_nota?, cve_orden, texto, creado_en?)
            cve_nota  = row[0] if len(row) >= 4 else None
            cve_orden = row[1] if len(row) >= 2 else None
            texto     = row[2] if len(row) >= 3 else ""
            creado_en = row[3] if len(row) >= 4 else None

        try:
            cve_nota = int(cve_nota) if cve_nota is not None and str(cve_nota).strip().isdigit() else None
        except Exception:
            cve_nota = None

        cve_orden = int(str(cve_orden))  # lanza si no es válido
        texto = (texto or "").strip()
        if not texto:
            texto = "(nota vacía)"

        # normaliza fecha
        if isinstance(creado_en, str):
            try:
                creado_en = datetime.fromisoformat(creado_en)
            except Exception:
                creado_en = None

        return cls(cve_nota=cve_nota, cve_orden=cve_orden, texto=texto, creado_en=creado_en)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_nota": self.cve_nota,
            "cve_orden": self.cve_orden,
            "texto": self.texto,
            "creado_en": self.creado_en.isoformat() if isinstance(self.creado_en, datetime) else None,
        }

    def __str__(self) -> str:
        return f"#{self.cve_nota or '—'} · {self.texto[:50]}"