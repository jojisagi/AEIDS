# model/repositories/nota_repo.py
from model.oracle_model import OracleDB

class NotaModelo:
    def __init__(self, db: OracleDB):
        self.db = db

    def _has_col(self, table: str, col: str) -> bool:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT COUNT(*) FROM USER_TAB_COLS WHERE TABLE_NAME=:t AND COLUMN_NAME=:c",
            {"t": table.upper(), "c": col.upper()},
        )
        return (cur.fetchone() or [0])[0] > 0

    def listar(self, cve_orden: int):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT nota, fecha FROM orden_nota WHERE cve_orden=:o ORDER BY fecha DESC", {"o": int(cve_orden)})
        rows = cur.fetchall() or []
        # Devuelve en dicts para la vista
        return [{"nota": r[0], "fecha": r[1]} for r in rows]

    def insertar(self, cve_orden: int, nota: str):
        conn = self.db.get_connection()
        cur = conn.cursor()
        if self._has_col("ORDEN_NOTA", "FECHA"):
            sql = "INSERT INTO orden_nota (cve_orden, nota, fecha) VALUES (:o, :n, SYSDATE)"
        else:
            sql = "INSERT INTO orden_nota (cve_orden, nota) VALUES (:o, :n)"
        cur.execute(sql, {"o": int(cve_orden), "n": nota})
        conn.commit()
        return 1