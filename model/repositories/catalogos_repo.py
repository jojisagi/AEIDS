# model/repositories/catalogos_repo.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
import oracledb


class CatalogosModelo:
    def __init__(self, db) -> None:
        self.db = db  # OracleDB con .get_connection()

    # ============== helpers internos ==============

    def _fetch_all(self, table_candidates: List[str]) -> Tuple[str, List[str], List[Tuple[Any, ...]]]:
        """
        Devuelve (tabla_encontrada, columnas_en_lower, filas) probando nombres alternos.
        """
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            for t in table_candidates:
                try:
                    cur.execute(f"SELECT * FROM {t}")
                    cols = [d[0].lower() for d in cur.description]
                    rows = cur.fetchall()
                    return t, cols, rows
                except oracledb.DatabaseError as e:
                    if "ORA-00942" in str(e):  # table or view does not exist
                        continue
                    raise
        raise RuntimeError(f"No se encontró ninguna tabla válida entre: {table_candidates}")

    @staticmethod
    def _pick_first(candidates: List[str], cols: List[str]) -> Optional[str]:
        for c in candidates:
            if c.lower() in cols:
                return c.lower()
        return None

    # Azúcar
    def _table_cols(self, table_candidates: List[str]) -> Tuple[str, List[str]]:
        t, cols, _ = self._fetch_all(table_candidates)
        return t, cols

    # Busca un ID por nombre (o devuelve el entero si ya lo es)
    def _lookup_id(
        self,
        table_cands: List[str],
        id_cands: List[str],
        name_cands: List[str],
        value: Any,
        extra_filters: Optional[Dict[str, Any]] = None,
        conn=None,
    ) -> Optional[int]:
        try:
            return int(str(value).strip())
        except Exception:
            pass

        table, cols = self._table_cols(table_cands)
        id_col = self._pick_first(id_cands, cols)
        name_col = self._pick_first(name_cands, cols)
        if not id_col or not name_col or value in (None, ""):
            return None

        sql = f"SELECT {id_col} FROM {table} WHERE UPPER(TRIM({name_col})) = UPPER(TRIM(:nom))"
        binds = {"nom": str(value)}
        if extra_filters:
            for k, v in extra_filters.items():
                if k in cols and v is not None:
                    sql += f" AND {k} = :{k}"
                    binds[k] = v

        local_conn = conn or self.db.get_connection()
        with local_conn.cursor() as cur:
            cur.execute(sql, binds)
            row = cur.fetchone()
            return int(row[0]) if row else None

    # Garantiza un ID: si no existe por nombre (con filtros extra), inserta (con COMMIT)
    def _ensure_id(
        self,
        table_cands: List[str],
        id_cands: List[str],
        name_cands: List[str],
        value: Any,
        extra_filters: Optional[Dict[str, Any]] = None,
        conn=None,
    ) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            pass

        table, cols = self._table_cols(table_cands)
        id_col = self._pick_first(id_cands, cols)
        name_col = self._pick_first(name_cands, cols)
        if not id_col or not name_col:
            raise RuntimeError(f"No se encontraron columnas mínimas en {table}")

        local_conn = conn or self.db.get_connection()

        found = self._lookup_id(table_cands, id_cands, name_cands, value, extra_filters, conn=local_conn)
        if found:
            return found

        with local_conn.cursor() as cur:
            cur.execute(f"SELECT NVL(MAX({id_col}), 0) + 1 FROM {table}")
            new_id = int(cur.fetchone()[0])

            cols_ins = [id_col, name_col]
            vals_ins = [new_id, str(value) if value not in (None, "") else f"{table} {new_id}"]

            if extra_filters:
                for k, v in extra_filters.items():
                    if k in cols and v is not None:
                        cols_ins.append(k)
                        vals_ins.append(v)

            ph = ", ".join([f":p{i}" for i in range(1, len(cols_ins) + 1)])
            sql = f"INSERT INTO {table} ({', '.join(cols_ins)}) VALUES ({ph})"
            binds = {f"p{i}": vals_ins[i-1] for i in range(1, len(vals_ins) + 1)}

            cur.execute(sql, binds)
            # muy importante: commit para que otras conexiones vean el registro
            local_conn.commit()
            return new_id

    # ============== catálogos públicos ==============

    def talleres(self) -> Dict[int, str]:
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            for name_col in ("nombre", "descripcion", "taller"):
                try:
                    cur.execute(f"SELECT cve_taller, {name_col} FROM taller ORDER BY 1")
                    return {int(r[0]): str(r[1]) for r in cur.fetchall()}
                except oracledb.DatabaseError as e:
                    if "ORA-00904" in str(e):
                        continue
                    if "ORA-00942" in str(e):
                        break
                    raise

        table, cols, rows = self._fetch_all(["taller", "talleres"])
        id_col = self._pick_first(["cve_taller", "id", "cve"], cols)
        txt_col = self._pick_first(["nombre", "descripcion", "taller"], cols)
        if not id_col:
            raise RuntimeError(f"No se encontró columna id en {table}")
        if not txt_col:
            return {int(r[cols.index(id_col)]): f"Taller {r[cols.index(id_col)]}" for r in rows}
        i_id = cols.index(id_col); i_tx = cols.index(txt_col)
        return {int(r[i_id]): str(r[i_tx]) for r in rows}

    def tipos(self) -> Dict[int, Tuple[float, str]]:
        table, cols, rows = self._fetch_all(["tipo_equipo", "tipo", "tipos"])
        id_col     = self._pick_first(["cve_tipo_equipo", "cve_tipo", "id", "cve"], cols)
        name_col   = self._pick_first(["descripcion", "nombre", "tipo"], cols)
        tarifa_col = self._pick_first(["tarifa", "precio", "costo"], cols)
        if not id_col or not name_col:
            raise RuntimeError(f"No se encontraron columnas mínimas (id/nombre) en {table}")

        i_id = cols.index(id_col); i_name = cols.index(name_col)
        i_tar = cols.index(tarifa_col) if tarifa_col else None

        out: Dict[int, Tuple[float, str]] = {}
        for r in rows:
            try:
                _id = int(r[i_id])
            except Exception:
                continue
            nombre = "" if r[i_name] is None else str(r[i_name])
            tarifa = 0.0
            if i_tar is not None and r[i_tar] is not None:
                try:
                    tarifa = float(r[i_tar])
                except Exception:
                    tarifa = 0.0
            out[_id] = (tarifa, nombre)
        return out

    def statuses(self) -> Dict[int, str]:
        table, cols, rows = self._fetch_all(["status", "estatus", "statuses"])
        id_col   = self._pick_first(["cve_status", "id", "cve"], cols)
        name_col = self._pick_first(["status", "descripcion", "nombre"], cols)
        if not id_col or not name_col:
            raise RuntimeError(f"No se encontraron columnas mínimas (id/nombre) en {table}")
        i_id = cols.index(id_col); i_nm = cols.index(name_col)
        out: Dict[int, str] = {}
        for r in rows:
            try:
                _id = int(r[i_id])
            except Exception:
                continue
            out[_id] = "" if r[i_nm] is None else str(r[i_nm])
        return out

    def paises(self) -> Dict[str, int]:
        table, cols, rows = self._fetch_all(["pais", "paises"])
        id_col   = self._pick_first(["cve_pais", "id", "cve"], cols)
        name_col = self._pick_first(["nombre", "descripcion", "pais"], cols)
        if not id_col or not name_col:
            raise RuntimeError(f"No se encontraron columnas mínimas (id/nombre) en {table}")
        i_id = cols.index(id_col); i_nm = cols.index(name_col)
        out: Dict[str, int] = {}
        for r in rows:
            try:
                _id = int(r[i_id])
            except Exception:
                continue
            nombre = f"Pais {_id}" if r[i_nm] is None else str(r[i_nm])
            out[nombre] = _id
        return out

    def estados(self, pais: int | str) -> Dict[str, int]:
        try:
            pais_id = int(str(pais).strip())
        except Exception:
            pais_id = None
        table, cols, rows = self._fetch_all(["estado", "estados"])
        id_col   = self._pick_first(["cve_estado", "id", "cve"], cols)
        name_col = self._pick_first(["nombre", "descripcion", "estado"], cols)
        pais_col = self._pick_first(["cve_pais", "id_pais", "pais"], cols)
        if not id_col or not name_col:
            raise RuntimeError(f"No se encontraron columnas mínimas (id/nombre) en {table}")
        if pais_id is not None and pais_col:
            i_pais = cols.index(pais_col)
            rows = [r for r in rows if r[i_pais] == pais_id]
        i_id = cols.index(id_col); i_nm = cols.index(name_col)
        out: Dict[str, int] = {}
        for r in rows:
            try:
                _id = int(r[i_id])
            except Exception:
                continue
            nombre = f"Estado {_id}" if r[i_nm] is None else str(r[i_nm])
            out[nombre] = _id
        return out

    def colonias_por_cp(self, cp) -> List[Tuple[int, str]]:
        try:
            table, cols, _ = self._fetch_all(["colonia", "colonias"])
        except RuntimeError:
            return []
        id_col   = self._pick_first(["cve_colonia", "id", "cve"], cols)
        name_col = self._pick_first(["nombre", "descripcion", "colonia"], cols)
        cp_col   = self._pick_first(["cp", "codigo_postal", "cod_postal", "cpostal"], cols)
        if not id_col or not name_col or not cp_col:
            return []

        sql = f"SELECT {id_col}, {name_col} FROM {table} WHERE {cp_col} = :cp ORDER BY {name_col}"
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, {"cp": str(cp)})
            return [(int(r[0]), str(r[1])) for r in cur.fetchall()]

    # ---------- Resolver/crear colonia + FKs relacionadas ----------

    def buscar_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        table, cols, _ = self._fetch_all(["colonia", "colonias"])
        id_col   = self._pick_first(["cve_colonia", "id", "cve"], cols)
        name_col = self._pick_first(["nombre", "descripcion", "colonia"], cols)
        cp_col   = self._pick_first(["cp", "codigo_postal", "cod_postal", "cpostal"], cols)
        if not id_col or not name_col or not cp_col:
            return None

        sql = f"""
            SELECT {id_col}
              FROM {table}
             WHERE {cp_col} = :cp
               AND UPPER(TRIM({name_col})) = UPPER(TRIM(:nom))
             FETCH FIRST 1 ROWS ONLY
        """
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, {"cp": str(cp), "nom": nombre})
            row = cur.fetchone()
            return int(row[0]) if row else None

    def insertar_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        """
        Inserta colonia cumpliendo posibles FKs (pais/estado/municipio). Hace COMMIT.
        """
        table, cols, _ = self._fetch_all(["colonia", "colonias"])

        id_col   = self._pick_first(["cve_colonia", "id", "cve"], cols)
        name_col = self._pick_first(["nombre", "descripcion", "colonia"], cols)
        cp_col   = self._pick_first(["cp", "codigo_postal", "cod_postal", "cpostal"], cols)
        if not id_col or not name_col or not cp_col:
            return None

        # ¿Existen columnas FK?
        mun_col  = self._pick_first(["cve_municipio", "id_municipio", "municipio"], cols)
        est_col  = self._pick_first(["cve_estado", "id_estado", "estado"], cols)
        pais_col = self._pick_first(["cve_pais", "id_pais", "pais"], cols)

        conn = self.db.get_connection()

        try:
            # Resolver/crear FKs con la MISMA conexión y COMMIT interno
            pais_id = None
            if pais_col is not None:
                pais_id = self._ensure_id(
                    ["pais", "paises"],
                    ["cve_pais", "id", "cve"],
                    ["nombre", "descripcion", "pais"],
                    pais or "N/A",
                    conn=conn,
                )

            est_id = None
            if est_col is not None:
                table_e, cols_e = self._table_cols(["estado", "estados"])
                pais_ref = self._pick_first(["cve_pais", "id_pais", "pais"], cols_e)
                extra = {pais_ref: pais_id} if pais_ref and pais_id is not None else None
                est_id = self._ensure_id(
                    ["estado", "estados"],
                    ["cve_estado", "id", "cve"],
                    ["nombre", "descripcion", "estado"],
                    estado or "N/A",
                    extra_filters=extra,
                    conn=conn,
                )

            mun_id = None
            if mun_col is not None:
                table_m, cols_m = self._table_cols(["municipio", "municipios"])
                est_ref = self._pick_first(["cve_estado", "id_estado", "estado"], cols_m)
                extra = {est_ref: est_id} if est_ref and est_id is not None else None
                mun_id = self._ensure_id(
                    ["municipio", "municipios"],
                    ["cve_municipio", "id", "cve"],
                    ["nombre", "descripcion", "municipio"],
                    municipio or "N/A",
                    extra_filters=extra,
                    conn=conn,
                )

            # Insertar colonia
            with conn.cursor() as cur:
                cur.execute(f"SELECT NVL(MAX({id_col}), 0) + 1 FROM {table}")
                new_id = int(cur.fetchone()[0])

                cols_to_insert = [id_col, name_col, cp_col]
                vals_to_insert = [new_id, nombre, str(cp)]

                if pais_col and pais_id is not None:
                    cols_to_insert.append(pais_col); vals_to_insert.append(pais_id)
                if est_col and est_id is not None:
                    cols_to_insert.append(est_col);  vals_to_insert.append(est_id)
                if mun_col and mun_id is not None:
                    cols_to_insert.append(mun_col);  vals_to_insert.append(mun_id)

                ph = ", ".join([f":p{i}" for i in range(1, len(cols_to_insert) + 1)])
                sql = f"INSERT INTO {table} ({', '.join(cols_to_insert)}) VALUES ({ph})"
                binds = {f"p{i}": vals_to_insert[i-1] for i in range(1, len(vals_to_insert) + 1)}

                cur.execute(sql, binds)
                conn.commit()  # <-- CLAVE para que otras conexiones lo vean
                return new_id

        except oracledb.DatabaseError as e:
            conn.rollback()
            # Si alguien insertó la misma (cp, nombre) en paralelo
            if "ORA-00001" in str(e):
                return self.buscar_colonia(cp, nombre, municipio, estado, pais)
            raise

    def resolve_or_create_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: str | int | None = None,
        pais: str | int | None = None,
    ) -> Optional[int]:
        cid = self.buscar_colonia(cp, nombre, municipio, estado, pais)
        if cid:
            return cid
        return self.insertar_colonia(cp, nombre, municipio, estado, pais)

    # ---------- Técnicos ----------

    def tecnicos_taller(self, cve_taller: int | str) -> List[Dict[str, Any]]:
        try:
            taller_id = int(str(cve_taller).strip())
        except Exception:
            taller_id = None

        conn = self.db.get_connection()
        with conn.cursor() as cur:
            if taller_id is not None:
                for t in ("empleado", "tecnicos", "tecnico"):
                    try:
                        cur.execute(f"SELECT * FROM {t} WHERE cve_taller = :1", [taller_id])
                        cols = [d[0].lower() for d in cur.description]
                        rows = cur.fetchall()
                        return self._map_tecnicos_rows(cols, rows)
                    except oracledb.DatabaseError as e:
                        if "ORA-00942" in str(e) or "ORA-00904" in str(e):
                            continue
                        raise

            for t in ("empleado", "tecnicos", "tecnico"):
                try:
                    cur.execute(f"SELECT * FROM {t}")
                    cols = [d[0].lower() for d in cur.description]
                    rows = cur.fetchall()
                    tall_col = self._pick_first(["cve_taller", "id_taller", "taller"], cols)
                    if tall_col and taller_id is not None:
                        i_t = cols.index(tall_col)
                        rows = [r for r in rows if r[i_t] == taller_id]
                    return self._map_tecnicos_rows(cols, rows)
                except oracledb.DatabaseError as e:
                    if "ORA-00942" in str(e):
                        continue
                    raise

        return []

    @staticmethod
    def _map_tecnicos_rows(cols: List[str], rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
        id_col = name_col = pat_col = None
        for cand in ("cve_empleado", "cve_tecnico", "id", "cve"):
            if cand in cols: id_col = cand; break
        for cand in ("nombre",):
            if cand in cols: name_col = cand; break
        for cand in ("paterno", "ap_paterno", "apellido_paterno"):
            if cand in cols: pat_col = cand; break

        i_id = cols.index(id_col) if id_col else None
        i_nm = cols.index(name_col) if name_col else None
        i_pt = cols.index(pat_col) if pat_col else None

        out: List[Dict[str, Any]] = []
        for r in rows:
            d: Dict[str, Any] = {}
            if i_id is not None: d["cve_empleado"] = r[i_id]
            if i_nm is not None: d["nombre"] = r[i_nm]
            if i_pt is not None: d["paterno"] = r[i_pt]
            out.append(d)
        return out