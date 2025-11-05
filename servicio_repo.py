# model/repositories/servicio_repo.py
from __future__ import annotations
from typing import Protocol
from .base import DBLike, fetchall_dict

class IServicioRepo(Protocol):
    def catalogo(self) -> list[dict]: ...
    def listar(self, cve_orden: int) -> list[dict]: ...
    def insertar(self, cve_orden: int, cve_servicio: int) -> int: ...
    def eliminar(self, cve_orden_servicio: int) -> int: ...

class ServicioModelo(IServicioRepo):
    def __init__(self, db: DBLike) -> None:
        self.db = db

    def catalogo(self) -> list[dict]:
        cur = self.db.get_connection().cursor()
        cur.execute("""
            SELECT cve_servicio, descripcion, precio
            FROM servicio
            ORDER BY descripcion
        """)
        return fetchall_dict(cur)

    def listar(self, cve_orden: int) -> list[dict]:
        cur = self.db.get_connection().cursor()
        cur.execute("""
            SELECT os.cve_orden_servicio, os.cve_orden, s.cve_servicio, s.descripcion, s.precio
            FROM orden_servicio os
            JOIN servicio s ON s.cve_servicio = os.cve_servicio
            WHERE os.cve_orden = :ord
            ORDER BY os.cve_orden_servicio DESC
        """, dict(ord=int(cve_orden)))
        return fetchall_dict(cur)

    def insertar(self, cve_orden: int, cve_servicio: int) -> int:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT NVL(MAX(cve_orden_servicio),0)+1 FROM orden_servicio")
        new_id = int(cur.fetchone()[0])
        cur.execute("""
            INSERT INTO orden_servicio (cve_orden_servicio, cve_orden, cve_servicio)
            VALUES (:id, :ord, :srv)
        """, dict(id=new_id, ord=int(cve_orden), srv=int(cve_servicio)))
        return new_id

    def eliminar(self, cve_orden_servicio: int) -> int:
        cur = self.db.get_connection().cursor()
        cur.execute("DELETE FROM orden_servicio WHERE cve_orden_servicio = :id",
                    dict(id=int(cve_orden_servicio)))
        return cur.rowcount or 0