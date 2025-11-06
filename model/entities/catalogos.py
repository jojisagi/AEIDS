# model/entities/catalogos.py
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


# --------- Tipo de equipo ---------
@dataclass(slots=True)
class TipoEquipo:
    cve_tipo_equipo: int
    descripcion: str
    tarifa: float

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "TipoEquipo":
        if isinstance(row, Mapping):
            cve = _get(row, "cve_tipo_equipo", "id", "cve")
            desc = _get(row, "descripcion", "nombre", "tipo")
            tarifa = _get(row, "tarifa", "precio_hora", "precio", "monto")
        else:
            # tupla esperada: (id, descripcion, tarifa)
            cve, desc, tarifa = row[0], row[1] if len(row) > 1 else "", row[2] if len(row) > 2 else 0
        return cls(int(cve), str(desc or "").strip(), float(tarifa or 0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_tipo_equipo": self.cve_tipo_equipo,
            "descripcion": self.descripcion,
            "tarifa": self.tarifa,
        }

    def __str__(self) -> str:
        return f"{self.descripcion} (${self.tarifa:.2f}/h)"


# --------- Taller ---------
@dataclass(slots=True)
class Taller:
    cve_taller: int
    nombre: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Taller":
        if isinstance(row, Mapping):
            cve = _get(row, "cve_taller", "id", "cve")
            nom = _get(row, "nombre", "descripcion", "taller")
        else:
            # tupla: (id, nombre)
            cve, nom = row[0], row[1] if len(row) > 1 else ""
        return cls(int(cve), str(nom or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return {"cve_taller": self.cve_taller, "nombre": self.nombre}

    def __str__(self) -> str:
        return self.nombre


# --------- Técnico ---------
@dataclass(slots=True)
class Tecnico:
    cve_empleado: int
    nombre: str
    paterno: str | None = None
    materno: str | None = None

    @property
    def nombre_completo(self) -> str:
        p = f" {self.paterno}" if self.paterno else ""
        m = f" {self.materno}" if self.materno else ""
        return f"{self.nombre}{p}{m}".strip()

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Tecnico":
        if isinstance(row, Mapping):
            cve = _get(row, "cve_empleado", "id_empleado", "id", "cve")
            nom = _get(row, "nombre", "name")
            pat = _get(row, "paterno", "apellido_paterno", "ap_paterno")
            mat = _get(row, "materno", "apellido_materno", "ap_materno")
        else:
            # tupla: (id, nombre, paterno?, materno?)
            cve = row[0]
            nom = row[1] if len(row) > 1 else ""
            pat = row[2] if len(row) > 2 else None
            mat = row[3] if len(row) > 3 else None
        return cls(int(cve), str(nom or "").strip(),
                   None if not pat else str(pat).strip(),
                   None if not mat else str(mat).strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cve_empleado": self.cve_empleado,
            "nombre": self.nombre,
            "paterno": self.paterno,
            "materno": self.materno,
        }

    def __str__(self) -> str:
        return self.nombre_completo


# --------- País ---------
@dataclass(slots=True)
class Pais:
    cve_pais: int
    nombre: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Pais":
        if isinstance(row, Mapping):
            cve = _get(row, "cve_pais", "id_pais", "id", "cve")
            nom = _get(row, "nombre", "pais", "descripcion")
        else:
            # tupla: (id, nombre)
            cve, nom = row[0], row[1] if len(row) > 1 else ""
        return cls(int(cve), str(nom or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return {"cve_pais": self.cve_pais, "nombre": self.nombre}

    def __str__(self) -> str:
        return self.nombre


# --------- Estado ---------
@dataclass(slots=True)
class Estado:
    cve_estado: int
    nombre: str
    cve_pais: int

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | Sequence[Any]) -> "Estado":
        if isinstance(row, Mapping):
            cve = _get(row, "cve_estado", "id_estado", "id", "cve")
            nom = _get(row, "nombre", "estado", "descripcion")
            pais = _get(row, "cve_pais", "pais", "id_pais")
        else:
            # tupla: (id_estado, nombre, cve_pais)
            cve = row[0]
            nom = row[1] if len(row) > 1 else ""
            pais = row[2] if len(row) > 2 else 0
        return cls(int(cve), str(nom or "").strip(), int(pais))

    def to_dict(self) -> dict[str, Any]:
        return {"cve_estado": self.cve_estado, "nombre": self.nombre, "cve_pais": self.cve_pais}

    def __str__(self) -> str:
        return self.nombre