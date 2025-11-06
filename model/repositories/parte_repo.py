# model/repositories/parte_repo.py
from __future__ import annotations
from typing import Any, List, Dict
import oracledb  # pip install oracledb

from model.oracle_model import OracleDB


class ParteModelo:
    def __init__(self, db: OracleDB):
        self.db = db

    # Catálogo de partes
    def catalogo(self) -> List[Dict[str, Any]]:
        cur = self.db.get_connection().cursor()
        # Ajusta columnas si tu tabla PARTE tiene otros nombres
        cur.execute(
            "SELECT cve_parte, part_no, descripcion, precio FROM parte ORDER BY descripcion"
        )
        rows = cur.fetchall()
        return [
            {
                "cve_parte": int(r[0]),
                "part_no": r[1],
                "descripcion": r[2],
                "precio": r[3],
            }
            for r in rows
        ]

    # Partes por orden (JOIN con parte)
    def listar(self, cve_orden: int) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        ord_id = int(cve_orden)

        # posibles nombres según distintos esquemas
        candidates = [
            ("orden_parte",  "cve_orden_parte", "cve_parte"),
            ("orden_partes", "cve_orden_parte", "cve_parte"),
            ("orden_pieza",  "cve_orden_pieza", "cve_parte"),
            ("orden_piezas", "cve_orden_pieza", "cve_parte"),
        ]

        last_err = None
        for tname, pk, fk in candidates:
            sql = f"""
                SELECT op.{pk}, p.cve_parte, p.part_no, p.descripcion, p.precio
                FROM {tname} op
                JOIN parte p ON p.cve_parte = op.{fk}
                WHERE op.cve_orden = :ord
                ORDER BY op.{pk} DESC
            """
            try:
                cur.execute(sql, {"ord": ord_id})
                rows = cur.fetchall()
                return [
                    {
                        "cve_orden_parte": int(r[0]),
                        "cve_parte": int(r[1]),
                        "part_no": r[2],
                        "descripcion": r[3],
                        "precio": r[4],
                    }
                    for r in rows
                ]
            except oracledb.DatabaseError as ex:
                err = ex.args[0]
                if getattr(err, "code", None) == 942:  # ORA-00942
                    last_err = ex
                    continue
                raise
        if last_err:
            raise last_err
        return []

    # Insertar parte a orden
    def insertar(self, cve_orden: int, cve_parte: int) -> int:
        conn = self.db.get_connection()
        cur = conn.cursor()
        ord_id = int(cve_orden)
        parte_id = int(cve_parte)

        candidates = [
            ("orden_parte",  "cve_parte"),
            ("orden_partes", "cve_parte"),
            ("orden_pieza",  "cve_parte"),
            ("orden_piezas", "cve_parte"),
        ]

        last_err = None
        for tname, fk in candidates:
            try:
                cur.execute(
                    f"INSERT INTO {tname} (cve_orden, {fk}) VALUES (:ord, :parte)",
                    {"ord": ord_id, "parte": parte_id},
                )
                return 1
            except oracledb.DatabaseError as ex:
                err = ex.args[0]
                if getattr(err, "code", None) == 942:
                    last_err = ex
                    continue
                raise
        if last_err:
            raise last_err
        return 0

    # Eliminar registro de parte en orden
    def eliminar(self, cve_orden_parte: int) -> int:
        conn = self.db.get_connection()
        cur = conn.cursor()
        pk_val = int(cve_orden_parte)

        candidates = [
            ("orden_parte",  "cve_orden_parte"),
            ("orden_partes", "cve_orden_parte"),
            ("orden_pieza",  "cve_orden_pieza"),
            ("orden_piezas", "cve_orden_pieza"),
        ]

        last_err = None
        for tname, pk in candidates:
            try:
                cur.execute(f"DELETE FROM {tname} WHERE {pk} = :id", {"id": pk_val})
                return cur.rowcount
            except oracledb.DatabaseError as ex:
                err = ex.args[0]
                if getattr(err, "code", None) == 942:
                    last_err = ex
                    continue
                raise
        if last_err:
            raise last_err
        return 0