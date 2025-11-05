# model/db/oracle.py
from __future__ import annotations
from typing import Any, Iterable, Sequence, Tuple, List
import oracledb  # pip install oracledb

class OracleDB:
    """
    Wrapper simple para python-oracledb (modo thin).
    API mínima usada por tu proyecto:
      - get_connection(), close_connection()
      - query(sql, params)
      - execute(sql, params), executemany(sql, seq_params)
      - commit(), rollback()
    """

    def __init__(self, hostname: str, port: int | str, service_name: str,
                 username: str, password: str):
        dsn = f"{hostname}:{int(port)}/{service_name}"
        self._conn = oracledb.connect(
            user=username,
            password=password,
            dsn=dsn,
            encoding="UTF-8",
        )

    # --- conexión ---
    def get_connection(self):
        return self._conn

    def close_connection(self):
        try:
            self._conn.close()
        except Exception:
            pass

    # --- helpers de ejecución ---
    def query(self, sql: str, params: Sequence[Any] | dict | None = None) -> Tuple[List[tuple], List[str]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or {})
            rows = cur.fetchall()
            cols = [d[0].lower() for d in (cur.description or [])]
        return rows, cols

    def execute(self, sql: str, params: Sequence[Any] | dict | None = None) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.rowcount

    def executemany(self, sql: str, params_iter: Iterable[Sequence[Any] | dict]) -> None:
        with self._conn.cursor() as cur:
            cur.executemany(sql, params_iter)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()