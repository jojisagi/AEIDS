# controller/catalogos_controller.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

class CatalogosControlador:
    def __init__(self, modelo) -> None:
        self.m = modelo

    # ------- catálogos existentes -------
    def tipos(self):
        return self.m.tipos()

    def talleres(self):
        return self.m.talleres()

    def paises(self):
        return self.m.paises()

    def estados(self, pais: int | str):
        return self.m.estados(pais)

    def tecnicos_taller(self, cve_taller: int):
        return self.m.tecnicos_taller(int(cve_taller))

    def statuses(self):
        return self.m.statuses()

    # ------- NUEVO: colonias -------
    def buscar_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        """
        Devuelve cve_colonia si existe. Si el modelo no implementa la función,
        regresa None silenciosamente.
        """
        if hasattr(self.m, "buscar_colonia"):
            return self.m.buscar_colonia(cp, nombre, municipio, estado, pais)
        return None

    def insertar_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        """
        Inserta colonia mínima y regresa su cve_colonia.
        Silencioso si el modelo no implementa el método.
        """
        if hasattr(self.m, "insertar_colonia"):
            return self.m.insertar_colonia(cp, nombre, municipio, estado, pais)
        return None

    def resolve_or_create_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        """
        Busca colonia (cp, nombre). Si no existe y el modelo lo soporta, la crea.
        """
        cid = self.buscar_colonia(cp, nombre, municipio, estado, pais)
        if cid:
            return cid
        return self.insertar_colonia(cp, nombre, municipio, estado, pais)