from dataclasses import dataclass
from typing import Optional

@dataclass
class Cliente:
    cve_cliente: int
    nombre: str
    paterno: str
    materno: str
    correo: str
    telefono: str

@dataclass
class OrdenData:
    cve_orden: int
    cve_status: int
    eq_marca: str
    eq_modelo: str
    cve_tipo_equipo: int
    notas_cliente: Optional[str]
    cve_taller: int
    cliente: Cliente

@dataclass
class NotaData:
    cve_nota: int
    cve_orden: int
    nota: str

@dataclass
class ParteData:
    cve_parte: int
    cve_orden: int
    desc: str
    spec: str

@dataclass
class ServicioData:
    cve_servicio: int
    cve_orden: int
    desc: str
    spec: str
