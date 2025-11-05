from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping

_DEFAULT_PERMS = {
    "Nueva_Nota": True, "Ver_Nota": True,
    "Nueva_Orden": True, "Reporte": True,
    "Nueva_Parte": True, "Ver_Parte": True,
    "Nuevo_Servicio": True, "Ver_Servicio": True,
}

# Puedes ajustar la matriz por rol aquí
_ROLE_MATRIX = {
    "admin": {k: True for k in _DEFAULT_PERMS},
    "operador": {
        "Nueva_Nota": True, "Ver_Nota": True,
        "Nueva_Orden": True, "Reporte": True,
        "Nueva_Parte": True, "Ver_Parte": True,
        "Nuevo_Servicio": True, "Ver_Servicio": True,
    },
    "consulta": {
        "Nueva_Nota": False, "Ver_Nota": True,
        "Nueva_Orden": False, "Reporte": True,
        "Nueva_Parte": False, "Ver_Parte": True,
        "Nuevo_Servicio": False, "Ver_Servicio": True,
    },
}

@dataclass(slots=True)
class Usuario:
    name: str
    rol: str = "operador"
    _permisos: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, m: Mapping[str, Any]) -> "Usuario":
        name = m.get("name") or m.get("usuario") or m.get("username") or "user"
        rol  = (m.get("rol") or m.get("role") or "operador").lower().strip()
        return cls(name=str(name), rol=rol)

    def permisos(self) -> dict[str, bool]:
        if self._permisos:
            return self._permisos
        base = _ROLE_MATRIX.get(self.rol.lower(), _ROLE_MATRIX["operador"])
        # copia defensiva
        self._permisos = dict(base)
        return self._permisos

    def __str__(self) -> str:
        return f"{self.name} ({self.rol})"