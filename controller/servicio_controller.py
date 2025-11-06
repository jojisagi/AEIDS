# controller/servicio_controller.py
from __future__ import annotations
from typing import Any, List


class ServicioControlador:
    def __init__(self, modelo) -> None:
        self.m = modelo

    # Catálogo
    def catalogo(self) -> List[dict]:
        return self.m.catalogo()

    # Por orden
    def listar(self, cve_orden: int) -> List[dict]:
        return self.m.listar(int(cve_orden))

    def insertar(self, cve_orden: int, cve_servicio: int) -> Any:
        return self.m.insertar(int(cve_orden), int(cve_servicio))

    def eliminar(self, cve_orden_servicio: int) -> Any:
        return self.m.eliminar(int(cve_orden_servicio))