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

# Catálogo de servicios
@dataclass(slots=True)
class Servicio:
    cve_servicio: int
    descripcion: str
    precio: float

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Servicio":
        if isinstance(row, Mapping):
            cve_servicio = _get(row, "cve_servicio", "id_servicio", "id")
            descripcion  = _get(row, "descripcion", "desc", "nombre")
            precio       = _get(row, "precio", "monto", "coste")
        else:
            # tupla: (cve_servicio, descripcion, precio)
            cve_servicio, descripcion, precio = (
                row[0], row[1] if len(row) > 1 else "", row[2] if len(row) > 2 else 0
            )
        return cls(
            cve_servicio=int(cve_servicio),
            descripcion=str(descripcion or "").strip(),
            precio=float(precio or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_servicio": self.cve_servicio,
            "descripcion": self.descripcion,
            "precio": self.precio,
        }

    def __str__(self) -> str:
        return f"{self.cve_servicio} · {self.descripcion} · ${self.precio:.2f}"

# Relación Servicio asignado a una Orden
@dataclass(slots=True)
class OrdenServicio:
    cve_orden_servicio: int | None
    cve_orden: int
    cve_servicio: int
    descripcion: str
    precio: float

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "OrdenServicio":
        if isinstance(row, Mapping):
            cve_orden_servicio = _get(row, "cve_orden_servicio", "id", "id_rel")
            cve_orden          = _get(row, "cve_orden", "orden", "id_orden")
            cve_servicio       = _get(row, "cve_servicio", "servicio", "id_servicio")
            descripcion        = _get(row, "descripcion", "desc", "detalle")
            precio             = _get(row, "precio", "monto")
        else:
            # tupla: (cve_orden_servicio?, cve_orden, cve_servicio, descripcion, precio)
            cve_orden_servicio = row[0] if len(row) >= 5 else None
            cve_orden          = row[1]
            cve_servicio       = row[2]
            descripcion        = row[3] if len(row) >= 4 else ""
            precio             = row[4] if len(row) >= 5 else 0

        try:
            cve_orden_servicio = int(cve_orden_servicio) if cve_orden_servicio is not None else None
        except Exception:
            cve_orden_servicio = None

        return cls(
            cve_orden_servicio=cve_orden_servicio,
            cve_orden=int(cve_orden),
            cve_servicio=int(cve_servicio),
            descripcion=str(descripcion or "").strip(),
            precio=float(precio or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_orden_servicio": self.cve_orden_servicio,
            "cve_orden": self.cve_orden,
            "cve_servicio": self.cve_servicio,
            "descripcion": self.descripcion,
            "precio": self.precio,
        }

    def __str__(self) -> str:
        return f"{self.cve_orden_servicio or '—'} · O{self.cve_orden} · S{self.cve_servicio} · {self.descripcion} · ${self.precio:.2f}"