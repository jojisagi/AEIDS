# controller/cliente_controller.py
from __future__ import annotations
from typing import Any


class ClienteControlador:
    def __init__(self, modelo) -> None:
        self.m = modelo

    def insertar_y_verificar(
        self,
        nombre: str, paterno: str, materno: str,
        correo: str, telefono: str,
        calle: str, num_calle: str, cp5: str,
        colonia: str, municipio: str, estado: str, pais: int | str,
    ) -> Any:
        """
        Debe devolver cve_cliente (int) o lanzar excepción desde el modelo si falla.
        """
        return self.m.insertar_y_verificar(
            nombre, paterno, materno, correo, telefono,
            calle, num_calle, cp5, colonia, municipio, estado, pais
        )