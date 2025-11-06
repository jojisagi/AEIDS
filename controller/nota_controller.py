# controller/nota_controller.py
from __future__ import annotations
from typing import Any, List


class NotaControlador:
    def __init__(self, modelo) -> None:
        self.m = modelo

    def listar(self, cve_orden: int) -> List[Any]:
        return self.m.listar(int(cve_orden))

    def insertar(self, cve_orden: int, nota: str) -> Any:
        return self.m.insertar(int(cve_orden), nota)

    def eliminar(self, cve_nota: int) -> Any:
        return self.m.eliminar(int(cve_nota))