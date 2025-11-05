# model/repositories/__init__.py

# Re-exporta las clases de cada módulo para poder hacer:
#   from model.repositories import OrdenModelo, NotaModelo, ...
from .orden_repo import OrdenModelo
from .nota_repo import NotaModelo
from .parte_repo import ParteModelo
from .servicio_repo import ServicioModelo
from .cliente_repo import ClienteModelo
from .catalogos_repo import CatalogosModelo

__all__ = [
    "OrdenModelo",
    "NotaModelo",
    "ParteModelo",
    "ServicioModelo",
    "ClienteModelo",
    "CatalogosModelo",
]