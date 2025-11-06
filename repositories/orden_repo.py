# model/repositories/orden_repo.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .base import DBLike, fetchall_dict

# Opcional: entidad usada por el dashboard
@dataclass(slots=True)
class OrdenResumen:
    cve_orden: int
    cve_status: int
    eq_marca: str
    eq_modelo: str
    cve_tipo_equipo: int
    cve_taller: int
    cliente: str
    horas: int
    tecnicos: list[str]

class IOrdenRepo(Protocol):
    def listar(self) -> list[OrdenResumen]: ...
    def actualizar(self, cve_orden: int, **kwargs) -> int: ...
    def insertar(self, cve_status: int, eq_marca: str, eq_modelo: str,
                 cve_tipo_equipo: int, notas_cliente: str,
                 cliente: int, cve_taller: int, cve_tecnico: int) -> int: ...
    def tecnicos_orden(self, cve_orden: int, incluir_horas: bool = False) -> list[str] | list[dict]: ...
    def cliente_id_por_orden(self, cve_orden: int) -> int | None: ...

class OrdenModelo(IOrdenRepo):
    """Implementación Oracle basada en OracleDB (db.get_connection())."""
    def __init__(self, db: DBLike) -> None:
        self.db = db

    def listar(self) -> list[OrdenResumen]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT  o.cve_orden,
                    o.cve_status,
                    o.eq_marca,
                    o.eq_modelo,
                    o.cve_tipo_equipo,
                    o.cve_taller,
                    c.nombre || ' ' || c.paterno || ' ' || NVL(c.materno,'') AS cliente,
                    NVL( (SELECT SUM(ot.horas)
                          FROM orden_tecnicos ot
                          WHERE ot.cve_orden = o.cve_orden), 0 ) AS horas_tot
            FROM orden o
            JOIN cliente c ON c.cve_cliente = o.cve_cliente
            ORDER BY o.cve_orden DESC
        """)
        base = fetchall_dict(cur)

        # Técnicos por orden
        tecnicos_map: dict[int, list[str]] = {}
        cur.execute("""
            SELECT ot.cve_orden, e.nombre, e.paterno
            FROM orden_tecnicos ot
            JOIN empleado e ON e.cve_empleado = ot.cve_empleado
        """)
        for r in fetchall_dict(cur):
            nom = (r.get("nombre") or "").strip()
            pat = (r.get("paterno") or "").strip()
            full = (nom + " " + pat).strip()
            tecnicos_map.setdefault(int(r["cve_orden"]), []).append(full)

        out: list[OrdenResumen] = []
        for r in base:
            out.append(
                OrdenResumen(
                    cve_orden=int(r["cve_orden"]),
                    cve_status=int(r["cve_status"]),
                    eq_marca=str(r.get("eq_marca") or ""),
                    eq_modelo=str(r.get("eq_modelo") or ""),
                    cve_tipo_equipo=int(r["cve_tipo_equipo"]),
                    cve_taller=int(r["cve_taller"]),
                    cliente=str(r.get("cliente") or "").strip(),
                    horas=int(r.get("horas_tot") or 0),
                    tecnicos=tecnicos_map.get(int(r["cve_orden"]), []),
                )
            )
        return out

    # === NUEVO: requerido por la fachada ===
    def cliente_id_por_orden(self, cve_orden: int) -> int | None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT cve_cliente FROM orden WHERE cve_orden = :id",
                {"id": int(cve_orden)},
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
        finally:
            try: cur.close()
            except: pass

    # === NUEVO: update con **kwargs mapeados a columnas ===
    def actualizar(self, cve_orden: int, **kwargs) -> int:
        """
        Update parcial de ORDEN. No hace commit (lo maneja la capa superior).
        Acepta claves:
          cve_status, eq_marca, eq_modelo, cve_tipo_equipo,
          notas_cliente, cve_taller, cve_cliente
        Maneja opcionalmente cve_tecnico (upsert en orden_tecnicos).
        """
        # mapeo de kwargs -> columnas
        colmap = {
            "cve_status": "cve_status",
            "eq_marca": "eq_marca",
            "eq_modelo": "eq_modelo",
            "cve_tipo_equipo": "cve_tipo_equipo",
            "notas_cliente": "notas_cliente",
            "cve_taller": "cve_taller",
            "cve_cliente": "cve_cliente",
        }

        sets, params = [], {"id": int(cve_orden)}
        for k, v in kwargs.items():
            col = colmap.get(k)
            if col is None:
                continue
            sets.append(f"{col} = :{k}")
            params[k] = v

        conn = self.db.get_connection()
        cur = conn.cursor()

        try:
            if sets:
                sql = f"UPDATE orden SET {', '.join(sets)} WHERE cve_orden = :id"
                cur.execute(sql, params)

            # cve_tecnico (si viene): dejamos un único técnico asignado (simple)
            if "cve_tecnico" in kwargs and kwargs["cve_tecnico"]:
                tec = int(kwargs["cve_tecnico"])
                # elimina asignaciones actuales y deja solo la nueva (horas preservadas = 0)
                cur.execute("DELETE FROM orden_tecnicos WHERE cve_orden = :id", {"id": int(cve_orden)})
                cur.execute("""
                    INSERT INTO orden_tecnicos (cve_orden, cve_empleado, horas)
                    VALUES (:ord, :tec, 0)
                """, {"ord": int(cve_orden), "tec": tec})

            return cur.rowcount or 0
        finally:
            try: cur.close()
            except: pass

    def insertar(self, cve_status: int, eq_marca: str, eq_modelo: str,
                 cve_tipo_equipo: int, notas_cliente: str,
                 cliente: int, cve_taller: int, cve_tecnico: int) -> int:
        conn = self.db.get_connection()
        cur = conn.cursor()
        # Si tienes secuencia, úsala; si no, dejamos MAX+1
        cur.execute("SELECT NVL(MAX(cve_orden), 0) + 1 FROM orden")
        new_id = int(cur.fetchone()[0])
        cur.execute("""
            INSERT INTO orden (cve_orden, cve_status, eq_marca, eq_modelo,
                               cve_tipo_equipo, notas_cliente, cve_cliente, cve_taller)
            VALUES (:id, :st, :ma, :mo, :ti, :no, :cli, :ta)
        """, dict(id=new_id, st=int(cve_status), ma=eq_marca, mo=eq_modelo,
                  ti=int(cve_tipo_equipo), no=notas_cliente, cli=int(cliente), ta=int(cve_taller)))
        if cve_tecnico:
            cur.execute("""
                INSERT INTO orden_tecnicos (cve_orden, cve_empleado, horas)
                VALUES (:ord, :tec, 0)
            """, dict(ord=new_id, tec=int(cve_tecnico)))
        return new_id

    def tecnicos_orden(self, cve_orden: int, incluir_horas: bool = False):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.nombre, e.paterno, ot.horas
            FROM orden_tecnicos ot
            JOIN empleado e ON e.cve_empleado = ot.cve_empleado
            WHERE ot.cve_orden = :ord
        """, dict(ord=int(cve_orden)))
        rows = fetchall_dict(cur)
        if incluir_horas:
            return rows
        return [((r.get("nombre") or "").strip() + " " + (r.get("paterno") or "").strip()).strip() for r in rows]