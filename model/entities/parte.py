from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

def _get(m: Mapping[str, Any], *names: str) -> Any:
    for n in names:
        if n in m: 
            return m[n]
        for k in m.keys():
            if str(k).lower() == n.lower():
                return m[k]
    return None

# Catálogo de partes
@dataclass(slots=True)
class Parte:
    cve_parte: int
    part_no: str | None
    descripcion: str
    precio: float

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Parte":
        if isinstance(row, Mapping):
            cve_parte   = _get(row, "cve_parte", "id_parte", "id")
            part_no     = _get(row, "part_no", "numero_parte")
            descripcion = _get(row, "descripcion", "desc", "nombre")
            precio      = _get(row, "precio", "monto", "coste")
        else:
            # tupla: (cve_parte, part_no, descripcion, precio)
            cve_parte, part_no, descripcion, precio = (
                row[0], row[1] if len(row) > 1 else None,
                row[2] if len(row) > 2 else "", row[3] if len(row) > 3 else 0
            )

        return cls(
            cve_parte=int(cve_parte),
            part_no=(None if part_no in ("", None) else str(part_no)),
            descripcion=str(descripcion or "").strip(),
            precio=float(precio or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_parte": self.cve_parte,
            "part_no": self.part_no,
            "descripcion": self.descripcion,
            "precio": self.precio,
        }

    def __str__(self) -> str:
        pno = f"{self.part_no} " if self.part_no else ""
        return f"{self.cve_parte} · {pno}{self.descripcion} · ${self.precio:.2f}"

# Relación Parte asignada a una Orden
@dataclass(slots=True)
class OrdenParte:
    cve_orden_parte: int | None
    cve_orden: int
    cve_parte: int
    descripcion: str
    precio: float

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "OrdenParte":
        if isinstance(row, Mapping):
            cve_orden_parte = _get(row, "cve_orden_parte", "id", "id_rel")
            cve_orden       = _get(row, "cve_orden", "orden", "id_orden")
            cve_parte       = _get(row, "cve_parte", "parte", "id_parte")
            descripcion     = _get(row, "descripcion", "desc", "detalle")
            precio          = _get(row, "precio", "monto")
        else:
            # tupla: (cve_orden_parte?, cve_orden, cve_parte, descripcion, precio)
            cve_orden_parte = row[0] if len(row) >= 5 else None
            cve_orden       = row[1]
            cve_parte       = row[2]
            descripcion     = row[3] if len(row) >= 4 else ""
            precio          = row[4] if len(row) >= 5 else 0

        try:
            cve_orden_parte = int(cve_orden_parte) if cve_orden_parte is not None else None
        except Exception:
            cve_orden_parte = None

        return cls(
            cve_orden_parte=cve_orden_parte,
            cve_orden=int(cve_orden),
            cve_parte=int(cve_parte),
            descripcion=str(descripcion or "").strip(),
            precio=float(precio or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_orden_parte": self.cve_orden_parte,
            "cve_orden": self.cve_orden,
            "cve_parte": self.cve_parte,
            "descripcion": self.descripcion,
            "precio": self.precio,
        }

    def __str__(self) -> str:
        return f"{self.cve_orden_parte or '—'} · O{self.cve_orden} · P{self.cve_parte} · {self.descripcion} · ${self.precio:.2f}"