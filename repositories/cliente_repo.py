from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import oracledb


class ClienteModelo:
    """
    Inserta clientes de forma tolerante al esquema:
    - Detecta columnas con varios alias (DIR_CALLE, CALLE, ...).
    - Si CLIENTE requiere CVE_COLONIA, busca/crea colonia (llenando NOT NULL).
    - Rellena automáticamente otras columnas NOT NULL que no hayamos mapeado.
    - NO hace commit.
    """

    def __init__(self, db) -> None:
        self.db = db  # OracleDB con .get_connection()

    # =================== helpers de metadata ===================

    def _table_columns(self, table: str) -> Dict[str, Tuple[str, str]]:
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT UPPER(column_name), UPPER(data_type), nullable
                FROM ALL_TAB_COLUMNS
                WHERE UPPER(table_name)=UPPER(:t)
                """,
                {"t": table},
            )
            return {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    def _has_col(self, table: str, col: str) -> bool:
        cols = self._table_columns(table)
        return col.upper() in cols

    @staticmethod
    def _pick_first(candidates: List[str], cols: Dict[str, Tuple[str, str]]) -> Optional[str]:
        for c in candidates:
            cu = c.upper()
            if cu in cols:
                return cu
        return None

    # =================== helpers de COLONIA ===================

    def _detect_colonia_table(self) -> tuple[str, Dict[str, Optional[str]]]:
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            for t in ("COLONIA", "COLONIAS"):
                try:
                    cur.execute(f"SELECT * FROM {t} WHERE 1=0")
                    cols = [d[0].upper() for d in cur.description]
                except oracledb.DatabaseError:
                    continue

                def pick(*cands):
                    for c in cands:
                        if c.upper() in cols:
                            return c.upper()
                    return None

                id_col = pick("CVE_COLONIA", "ID", "CVE")
                namecol = pick("NOMBRE", "DESCRIPCION", "COLONIA")
                cp_col = pick("CP", "CODIGO_POSTAL", "COD_POSTAL", "CPOSTAL")
                if id_col and namecol:
                    return t, {"id": id_col, "name": namecol, "cp": cp_col}
        raise RuntimeError("No se encontró tabla de colonias (COLONIA/COLONIAS).")

    def _first_nonnull_or_min(self, table: str, col: str):
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SELECT MIN({col}) FROM {table} WHERE {col} IS NOT NULL")
            v = cur.fetchone()[0]
            if v is not None:
                return v
            cur.execute(
                f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL FETCH FIRST 1 ROWS ONLY"
            )
            r = cur.fetchone()
            return r[0] if r else None

    def _buscar_colonia_id(self, nombre_colonia: str, cp: Optional[str]) -> Optional[int]:
        try:
            table, basic = self._detect_colonia_table()
        except RuntimeError:
            return None

        namecol = basic["name"]
        cpcol = basic["cp"]
        if not namecol:
            return None

        conn = self.db.get_connection()
        with conn.cursor() as cur:
            if cpcol and cp is not None:
                cur.execute(
                    f"""
                    SELECT {basic['id']}
                    FROM {table}
                    WHERE UPPER(TRIM({namecol})) = UPPER(TRIM(:n))
                      AND {cpcol} = :cp
                    FETCH FIRST 1 ROWS ONLY
                    """,
                    {"n": nombre_colonia, "cp": str(cp)},
                )
            else:
                cur.execute(
                    f"""
                    SELECT {basic['id']}
                    FROM {table}
                    WHERE UPPER(TRIM({namecol})) = UPPER(TRIM(:n))
                    FETCH FIRST 1 ROWS ONLY
                    """,
                    {"n": nombre_colonia},
                )
            r = cur.fetchone()
            return int(r[0]) if r else None

    def _crear_colonia_flexible(
        self,
        nombre_colonia: str,
        cp: Optional[str],
        municipio: Optional[str],
        estado: Optional[str | int],
        pais: Optional[str | int],
    ) -> Optional[int]:
        if not nombre_colonia:
            return None

        table, basic = self._detect_colonia_table()
        cols_meta = self._table_columns(table)

        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SELECT NVL(MAX({basic['id']}),0)+1 FROM {table}")
            new_id = int(cur.fetchone()[0])

            insert_cols = [basic["id"], basic["name"]]
            insert_vals = [":p_id", ":p_name"]
            binds = {"p_id": new_id, "p_name": nombre_colonia}

            if basic["cp"] and basic["cp"] in cols_meta:
                insert_cols.append(basic["cp"])
                insert_vals.append(":p_cp")
                binds["p_cp"] = None if cp is None else str(cp)

            def _add_opt(colnames: List[str], raw_val: Any):
                col = self._pick_first(colnames, cols_meta) if colnames else None
                if not col or raw_val in (None, ""):
                    return
                dtype, nullable = cols_meta[col]
                v = raw_val
                if col.startswith(("CVE_", "ID_")) or dtype.startswith("NUMBER"):
                    try:
                        v = int(str(raw_val).strip())
                    except Exception:
                        return
                insert_cols.append(col)
                insert_vals.append(f":p_{col.lower()}")
                binds[f"p_{col.lower()}"] = v

            _add_opt(["CVE_MUNICIPIO", "ID_MUNICIPIO", "MUNICIPIO"], municipio)
            _add_opt(["CVE_ESTADO", "ID_ESTADO", "ESTADO"], estado)
            _add_opt(["CVE_PAIS", "ID_PAIS", "PAIS"], pais)

            # completar NOT NULL que falten
            already = set(insert_cols)
            for col_name, (_dtype, nullable) in cols_meta.items():
                if nullable == "N" and col_name not in already:
                    dv = self._first_nonnull_or_min(table, col_name)
                    if dv is not None:
                        insert_cols.append(col_name)
                        insert_vals.append(f":p_{col_name.lower()}")
                        binds[f"p_{col_name.lower()}"] = dv

            sql = f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})"
            try:
                cur.execute(sql, binds)
                return new_id
            except oracledb.DatabaseError as e:
                if "ORA-00001" in str(e):
                    try:
                        if basic["cp"] and basic["cp"] in cols_meta and cp is not None:
                            cur.execute(
                                f"""
                                SELECT {basic['id']}
                                FROM {table}
                                WHERE UPPER(TRIM({basic['name']})) = UPPER(TRIM(:n))
                                  AND {basic['cp']} = :cp
                                FETCH FIRST 1 ROWS ONLY
                                """,
                                {"n": nombre_colonia, "cp": str(cp)},
                            )
                        else:
                            cur.execute(
                                f"""
                                SELECT {basic['id']}
                                FROM {table}
                                WHERE UPPER(TRIM({basic['name']})) = UPPER(TRIM(:n))
                                FETCH FIRST 1 ROWS ONLY
                                """,
                                {"n": nombre_colonia},
                            )
                        r = cur.fetchone()
                        return int(r[0]) if r else None
                    except Exception:
                        return None
                return None

    # =================== inserción de CLIENTE ===================

    def insertar_y_verificar(
        self,
        nombre: str,
        paterno: str,
        materno: str,
        correo: str,
        telefono: str,
        calle: str,
        numero_calle: str,
        cp: str,
        colonia: str | int,
        municipio: str,
        estado: str | int,
        pais: str | int,
    ) -> Optional[int]:
        table = "CLIENTE"
        cols_meta = self._table_columns(table)

        id_col = self._pick_first(["CVE_CLIENTE", "ID", "CVE"], cols_meta)
        if not id_col:
            raise RuntimeError("No se encontró columna id en CLIENTE (CVE_CLIENTE/ID/CVE).")

        nombre_col = self._pick_first(["NOMBRE"], cols_meta)
        pat_col = self._pick_first(["PATERNO", "APELLIDO_PATERNO"], cols_meta)
        mat_col = self._pick_first(["MATERNO", "APELLIDO_MATERNO"], cols_meta)
        tel_col = self._pick_first(["TELEFONO", "TEL"], cols_meta)
        cor_col = self._pick_first(["CORREO", "EMAIL", "E_MAIL"], cols_meta)

        # >>> candidatos ampliados (incluye DIR_CALLE / DIR_NUMERO / DIR_CP)
        calle_col = self._pick_first(
            ["DIR_CALLE", "CALLE", "DIRECCION", "DOMICILIO", "DIR"], cols_meta
        )
        num_col = self._pick_first(
            ["DIR_NUMERO", "NUMERO", "NUMERO_CALLE", "NUM_EXT", "NUMEXTERIOR", "N_EXTERIOR"],
            cols_meta,
        )
        cp_col_cli = self._pick_first(
            ["DIR_CP", "CLI_CP", "CP", "CODIGO_POSTAL", "COD_POSTAL", "CPOSTAL"], cols_meta
        )

        col_text_col = self._pick_first(["COLONIA"], cols_meta)
        cve_colonia_fk = "CVE_COLONIA" if self._has_col(table, "CVE_COLONIA") else None

        municipio_col = self._pick_first(["MUNICIPIO"], cols_meta)
        estado_col = self._pick_first(["ESTADO"], cols_meta)
        pais_col = self._pick_first(["PAIS"], cols_meta)

        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SELECT NVL(MAX({id_col}),0)+1 FROM {table}")
            new_id = int(cur.fetchone()[0])

            insert_cols: List[str] = [id_col]
            insert_vals: List[str] = [":p_id"]
            binds: Dict[str, Any] = {"p_id": new_id}

            def _add(colname: Optional[str], value: Any, bind: str):
                if not colname:
                    return
                insert_cols.append(colname)
                insert_vals.append(f":{bind}")
                binds[bind] = value

            # datos base
            _add(nombre_col, nombre, "p_nombre")
            _add(pat_col, paterno, "p_paterno")
            _add(mat_col, materno, "p_materno")
            _add(tel_col, telefono, "p_tel")
            _add(cor_col, correo, "p_correo")
            _add(calle_col, calle, "p_calle")
            _add(num_col, numero_calle, "p_num")
            _add(cp_col_cli, None if cp is None else str(cp), "p_cpcli")

            _add(municipio_col, municipio, "p_mpio")
            _add(estado_col, str(estado), "p_estado")
            _add(pais_col, str(pais), "p_pais")

            # --- colonia ---
            if cve_colonia_fk:
                cve_colonia_id: Optional[int] = None

                if isinstance(colonia, int) or (isinstance(colonia, str) and str(colonia).isdigit()):
                    cve_colonia_id = int(colonia)
                else:
                    cve_colonia_id = self._buscar_colonia_id(str(colonia).strip(), cp)
                    if cve_colonia_id is None:
                        cve_colonia_id = self._crear_colonia_flexible(
                            nombre_colonia=str(colonia).strip(),
                            cp=cp,
                            municipio=municipio,
                            estado=estado,
                            pais=pais,
                        )

                if cve_colonia_id is None:
                    if col_text_col:
                        _add(col_text_col, str(colonia).strip(), "p_colonia_txt")
                    else:
                        raise ValueError(
                            "No se pudo resolver 'CVE_COLONIA' (no hay colonia para ese CP/nombre)."
                        )
                else:
                    _add(cve_colonia_fk, cve_colonia_id, "p_cve_colonia")
            else:
                if col_text_col:
                    _add(col_text_col, str(colonia).strip(), "p_colonia_txt")

            # === Plan B: completar cualquier NOT NULL faltante ===
            already = set(insert_cols)
            for col_name, (dtype, nullable) in cols_meta.items():
                if nullable == "N" and col_name not in already:
                    dv: Any = None
                    name = col_name.upper()

                    # intentar derivar desde los datos que ya tenemos
                    if "CALLE" in name:
                        dv = calle
                    elif "NUM" in name:
                        dv = numero_calle
                    elif name in ("DIR_CP", "CLI_CP", "CP", "CODIGO_POSTAL", "COD_POSTAL", "CPOSTAL"):
                        dv = None if cp is None else str(cp)
                    elif "MUNICIPIO" in name:
                        dv = municipio
                    elif "ESTADO" in name:
                        dv = str(estado)
                    elif "PAIS" in name:
                        dv = str(pais)

                    # si sigue vacío, usa un valor existente de la tabla
                    if dv in (None, ""):
                        dv = self._first_nonnull_or_min(table, col_name)

                    if dv is not None:
                        insert_cols.append(col_name)
                        insert_vals.append(f":p_{col_name.lower()}")
                        binds[f"p_{col_name.lower()}"] = dv
                    # Si dv sigue None y la tabla no tiene valores previos,
                    # Oracle fallará — pero en la práctica suele haber registros.

            sql = f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})"
            cur.execute(sql, binds)
            return new_id