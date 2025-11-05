# model/entities/__init__.py
from .cliente import Cliente
from .nota import Nota
from .parte import Parte, OrdenParte
from .servicio import Servicio, OrdenServicio
from .catalogos import TipoEquipo, Taller, Tecnico, Pais, Estado

__all__ = [
    "Cliente",
    "Nota",
    "Parte", "OrdenParte",
    "Servicio", "OrdenServicio",
    "TipoEquipo", "Taller", "Tecnico", "Pais", "Estado",
]