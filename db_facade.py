# controller/db_facade.py
from __future__ import annotations
from typing import Any, Dict

from model.oracle_model import OracleDB
from model.repositories import (
    OrdenModelo, NotaModelo, ParteModelo, ServicioModelo,
    ClienteModelo, CatalogosModelo
)
from controller.orden_controller import OrdenControlador
from controller.nota_controller import NotaControlador
from controller.parte_controller import ParteControlador
from controller.servicio_controller import ServicioControlador
from controller.cliente_controller import ClienteControlador
from controller.catalogos_controller import CatalogosControlador


class DBFacade:
    """
    Fachada para la UI.
    - Normaliza catálogos a: dict[int, str] (id -> nombre).
    - Incluye helpers para alta de estado y normalización de colonia/CP.
    - Métodos tolerantes a backends incompletos (fallback directo con SQL).
    """

    # ========================== Init / Wiring ==========================
    def __init__(self, hostname: str, port: str | int, service_name: str,
                 username: str, password: str) -> None:
        self._db = OracleDB(
            hostname=hostname, port=port, service_name=service_name,
            username=username, password=password
        )

        om = OrdenModelo(self._db)
        nm = NotaModelo(self._db)
        pm = ParteModelo(self._db)
        sm = ServicioModelo(self._db)
        cm = ClienteModelo(self._db)
        catm = CatalogosModelo(self._db)

        self._orden = OrdenControlador(om)
        self._nota = NotaControlador(nm)
        self._parte = ParteControlador(pm)
        self._servicio = ServicioControlador(sm)
        self._cliente = ClienteControlador(cm)
        self._catalogos = CatalogosControlador(catm)

    # ==================== Helpers de normalización =====================
    @staticmethod
    def _intish(val) -> bool:
        try:
            int(str(val).strip())
            return True
        except Exception:
            return False

    @staticmethod
    def _str_clean(val) -> str:
        return "" if val is None else str(val).strip()

    @staticmethod
    def _clean_display_name(txt: str) -> str:
        """
        Limpia nombres que vienen como '1 Computadora' o '01 - Computadora'
        para que el UI muestre solo 'Computadora'.
        """
        s = (txt or "").strip()
        # quita prefijos numéricos y separadores comunes
        while True:
            orig = s
            # elimina 'NN - ' o 'NN ' al inicio
            if len(s) >= 2 and s[0].isdigit():
                i = 0
                while i < len(s) and s[i].isdigit():
                    i += 1
                # espacios / guiones / puntos tras el número
                while i < len(s) and s[i] in " .-_/|:":
                    i += 1
                s = s[i:].lstrip()
            s = s.strip()
            if s == orig:
                break
        return s

    def _id_name_from_value(self, v) -> str:
        """Extrae texto de nombre desde múltiples formatos (tuplas/listas/dicts)."""
        if isinstance(v, (list, tuple)):
            if len(v) > 1 and isinstance(v[1], (str, bytes)):
                return self._clean_display_name(self._str_clean(v[1]))
            for it in v:
                if isinstance(it, (str, bytes)):
                    return self._clean_display_name(self._str_clean(it))
            return self._clean_display_name(self._str_clean(v[0])) if v else ""
        if isinstance(v, dict):
            for key in ("nombre", "descripcion", "estado", "tipo", "pais", "taller", "status"):
                if key in v and v[key] is not None:
                    return self._clean_display_name(self._str_clean(v[key]))
            for it in v.values():
                if isinstance(it, (str, bytes)):
                    return self._clean_display_name(self._str_clean(it))
            return self._clean_display_name(self._str_clean(v))
        return self._clean_display_name(self._str_clean(v))

    def _normalize_catalog(self, raw) -> Dict[int, str]:
        """
        Convierte dict/list/tuplas/dicts a {id:int -> nombre:str}.
        También invierte diccionarios {nombre->id} si es necesario.
        """
        out: dict[int, str] = {}
        if raw is None:
            return out

        # dict
        if isinstance(raw, dict):
            for k, v in raw.items():
                if self._intish(k):
                    out[int(str(k).strip())] = self._id_name_from_value(v)
                elif self._intish(v):
                    out[int(str(v).strip())] = self._id_name_from_value(k)
                else:
                    name = self._id_name_from_value(v)
                    out[-abs(hash((k, name))) % (10**8)] = name
            return out

        # list/tuple
        if isinstance(raw, (list, tuple)):
            for it in raw:
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    k, v = it[0], it[1]
                    if self._intish(k):
                        out[int(str(k).strip())] = self._id_name_from_value(v)
                    elif self._intish(v):
                        out[int(str(v).strip())] = self._id_name_from_value(k)
                    else:
                        name = self._id_name_from_value(it)
                        out[-abs(hash(tuple(it))) % (10**8)] = name
                elif isinstance(it, dict):
                    id_keys = ("id", "cve_id", "cve_estado", "cve_pais", "cve_tipo",
                               "cve_tipo_equipo", "cve_taller", "cve_status")
                    name_keys = ("nombre", "descripcion", "estado", "tipo", "pais", "taller", "status")
                    _id = None
                    for k in id_keys:
                        if k in it and self._intish(it[k]):
                            _id = int(str(it[k]).strip())
                            break
                    _nm = None
                    for k in name_keys:
                        if k in it and it[k]:
                            _nm = self._id_name_from_value(it[k])
                            break
                    if _id is not None and _nm is not None:
                        out[_id] = _nm
                    else:
                        _id2, _nm2 = None, None
                        for v in it.values():
                            if _id2 is None and self._intish(v):
                                _id2 = int(str(v).strip())
                            if _nm2 is None and isinstance(v, (str, bytes)):
                                _nm2 = self._id_name_from_value(v)
                        if _id2 is not None and _nm2 is not None:
                            out[_id2] = _nm2
                else:
                    name = self._id_name_from_value(it)
                    out[-abs(hash(name)) % (10**8)] = name
            return out

        out[-abs(hash(str(raw))) % (10**8)] = self._id_name_from_value(raw)
        return out

    # -------- tipos normalizado a {id: (tarifa, nombre)} ----------
    def _normalize_tipos(self, raw) -> dict[int, tuple[float, str]]:
        out: dict[int, tuple[float, str]] = {}
        if not raw:
            return out

        def _pair(v) -> tuple[float, str]:
            tarifa: float = 0.0
            nombre: str = ""
            if isinstance(v, (list, tuple)):
                # intenta [tarifa, nombre] o [id?, nombre, tarifa]
                nums = [x for x in v if isinstance(x, (int, float)) or str(x).replace('.', '', 1).isdigit()]
                txts = [x for x in v if isinstance(x, str)]
                if txts:
                    nombre = self._clean_display_name(txts[-1])
                if nums:
                    tarifa = float(nums[-1])
            elif isinstance(v, dict):
                if "tarifa" in v and v["tarifa"] is not None:
                    try: tarifa = float(v["tarifa"])
                    except Exception: tarifa = 0.0
                for k in ("nombre", "descripcion", "tipo"):
                    if k in v and v[k]:
                        nombre = self._clean_display_name(str(v[k]))
                        break
            elif isinstance(v, str):
                nombre = self._clean_display_name(v)
            else:
                nombre = self._clean_display_name(str(v))
            return (tarifa, nombre)

        if isinstance(raw, dict):
            for k, v in raw.items():
                if self._intish(k):
                    out[int(str(k).strip())] = _pair(v)
                elif self._intish(v):
                    out[int(str(v).strip())] = _pair(k)
        else:
            # lista de pares / dicts
            for it in (raw or []):
                if isinstance(it, (list, tuple)) and len(it) >= 2 and self._intish(it[0]):
                    out[int(str(it[0]).strip())] = _pair(it[1])
                elif isinstance(it, dict):
                    # busca id y nombre
                    id_keys = ("id", "cve_tipo_equipo", "cve_tipo")
                    _id = None
                    for kk in id_keys:
                        if kk in it and self._intish(it[kk]):
                            _id = int(str(it[kk]).strip())
                            break
                    if _id is not None:
                        out[_id] = _pair(it)

        return out

    # ============================ Conexión =============================
    def get_connection(self):
        return self._db.get_connection()

    def close_connection(self):
        return self._db.close_connection()

    # ============================ Órdenes ==============================
    def ordenes(self):
        return self._orden.listar()

    def insertar_orden(self, *args, **kwargs):
        return self._orden.insertar(*args, **kwargs)

    def tecnicos_orden(self, cve_orden, horas: bool = False):
        return self._orden.tecnicos_orden(cve_orden, horas)

    def actualizar_orden(self, cve_orden: int, **kwargs):
        """
        Acepta: cve_status, eq_marca, eq_modelo, cve_tipo_equipo,
                notas_cliente, cve_taller, cve_tecnico
        """
        return self._orden.m.actualizar(
            int(cve_orden),
            marca=str(kwargs.get("eq_marca", "") or ""),
            modelo=str(kwargs.get("eq_modelo", "") or ""),
            cve_tipo_equipo=int(kwargs.get("cve_tipo_equipo")),
            cve_status=int(kwargs.get("cve_status")),
        )

    # ============================== Notas =============================
    def notas(self, cve_orden):
        return self._nota.listar(cve_orden)

    def insertar_nota(self, cve_orden, nota):
        return self._nota.insertar(cve_orden, nota)

    def eliminar_nota(self, cve_nota):
        return self._nota.eliminar(cve_nota)

    # ============================== Partes ============================
    def partes(self):
        return self._parte.catalogo()

    def partes_orden(self, cve_orden):
        return self._parte.listar(cve_orden)

    def parte_orden(self, *args, **kwargs):
        return self._parte.insertar(*args, **kwargs)

    def eliminar_parte(self, cve_orden_parte):
        return self._parte.eliminar(cve_orden_parte)

    # ============================= Servicios ==========================
    def servicios(self):
        return self._servicio.catalogo()

    def servicios_orden(self, cve_orden):
        return self._servicio.listar(cve_orden)

    def servicio_orden(self, *args, **kwargs):
        return self._servicio.insertar(*args, **kwargs)

    def eliminar_servicio(self, cve_orden_servicio):
        return self._servicio.eliminar(cve_orden_servicio)

    # ============================== Cliente ===========================
    def insertar_cliente_y_verificar_datos(self, *args, **kwargs):
        return self._cliente.insertar_y_verificar(*args, **kwargs)

    # --------- Column map dinámico para CLIENTE (evita ORA-00904) -----
    def _cliente_colmap(self) -> dict:
        """
        Lee USER_TAB_COLUMNS para mapear nombres canónicos -> columna real.
        { 'nombre': 'NOMBRE', 'num_calle': 'NO_CALLE', ... }
        """
        conn = self._db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT UPPER(column_name) FROM user_tab_columns WHERE UPPER(table_name)='CLIENTE'"
        )
        cols = {r[0] for r in cur.fetchall() or []}

        def pick(*cands):
            for c in cands:
                uc = c.upper()
                if uc in cols:
                    return uc
            return None

        return {
            "pk":        pick("CVE_CLIENTE", "ID", "CLIENTE_ID"),
            "nombre":    pick("NOMBRE"),
            "paterno":   pick("PATERNO", "APELLIDO_PATERNO", "APE_PAT", "AP_PATERNO"),
            "materno":   pick("MATERNO", "APELLIDO_MATERNO", "APE_MAT", "AP_MATERNO"),
            "correo":    pick("CORREO", "EMAIL", "E_MAIL"),
            "telefono":  pick("TELEFONO", "TEL", "PHONE"),
            "calle":     pick("CALLE", "DIRECCION", "DOMICILIO", "DIRECCION1"),
            "num_calle": pick("NUM_CALLE", "NO_CALLE", "NUMERO", "NUMERO_CALLE", "NRO_CALLE"),
        }

    def cliente_id_por_orden(self, cve_orden: int) -> int | None:
        """
        Usa el controlador si existe; si no, lee directo.
        """
        try:
            return self._orden.cliente_id_por_orden(int(cve_orden))  # type: ignore[attr-defined]
        except Exception:
            conn = self._db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT cve_cliente FROM orden WHERE cve_orden = :o", {"o": int(cve_orden)})
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    def actualizar_cliente(self, cve_cliente: int, **kwargs):
        """
        UPDATE flexible que usa los nombres reales de columnas en CLIENTE.
        Acepta: nombre, paterno, materno, correo, telefono, calle, num_calle
        """
        cmap = self._cliente_colmap()
        if not cmap.get("pk"):
            raise RuntimeError("No se encontró la PK de CLIENTE.")

        fields = {
            "nombre":    kwargs.get("nombre"),
            "paterno":   kwargs.get("paterno"),
            "materno":   kwargs.get("materno"),
            "correo":    kwargs.get("correo"),
            "telefono":  kwargs.get("telefono"),
            "calle":     kwargs.get("calle"),
            "num_calle": kwargs.get("num_calle"),
        }

        sets, binds = [], {"IDVAL": int(cve_cliente)}
        for canonical, value in fields.items():
            col = cmap.get(canonical)
            if col is not None and value is not None:
                sets.append(f'{col} = :{canonical}')
                binds[canonical] = value

        if not sets:
            return 0  # nada que actualizar

        sql = f"UPDATE CLIENTE SET {', '.join(sets)} WHERE {cmap['pk']} = :IDVAL"
        conn = self._db.get_connection()
        cur = conn.cursor()
        cur.execute(sql, binds)
        return cur.rowcount or 0

    # ======= Catálogos (normalizados) y directos a tablas =========
    def tipos(self) -> dict[int, tuple[float, str]]:
        """
        Devuelve {id: (tarifa, nombre)}. El nombre viene limpio para UI
        (p.ej., 'Computadora' sin prefijos numéricos).
        """
        raw = self._catalogos.tipos()
        return self._normalize_tipos(raw)

    def talleres(self) -> dict[int, str]:
        return self._normalize_catalog(self._catalogos.talleres())

    def tecnicos_taller(self, cve_taller):
        return self._catalogos.tecnicos_taller(cve_taller)

    def statuses(self) -> dict[int, str]:
        return self._normalize_catalog(self._catalogos.statuses())

    def paises(self) -> dict[int, str]:
        conn = self._db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT cve_pais, pais FROM pais ORDER BY pais")
            rows = cur.fetchall() or []
            return {int(r[0]): (r[1] or "") for r in rows}
        finally:
            try: cur.close()
            except Exception: pass

    def estados(self, pais) -> dict[int, str]:
        try:
            pid = int(str(pais).strip())
        except Exception:
            return {}
        conn = self._db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT cve_estado, estado FROM estado WHERE cve_pais=:p ORDER BY estado",
                {"p": pid},
            )
            rows = cur.fetchall() or []
            return {int(r[0]): (r[1] or "") for r in rows}
        finally:
            try: cur.close()
            except Exception: pass

    # ===================== Helpers: estado/colonia ====================
    def upsert_estado(self, pais: int | str, nombre: str) -> int | None:
        if not nombre or not str(nombre).strip():
            return None

        conn = self._db.get_connection()
        cur = conn.cursor()

        try:
            pais_id = int(str(pais).strip())
        except Exception:
            return None

        nombre_clean = str(nombre).strip()
        nombre_key = nombre_clean.lower()

        cur.execute(
            "SELECT cve_estado FROM estado "
            "WHERE cve_pais = :p AND LOWER(TRIM(estado)) = :n FETCH FIRST 1 ROWS ONLY",
            {"p": pais_id, "n": nombre_key},
        )
        row = cur.fetchone()
        if row:
            return int(row[0])

        try:
            cur.execute(
                "INSERT INTO estado (cve_estado, cve_pais, estado) "
                "VALUES (estado_cve_estado_seq.NEXTVAL, :p, :n)",
                {"p": pais_id, "n": nombre_clean},
            )
            cur.execute("SELECT estado_cve_estado_seq.CURRVAL FROM dual")
            return int(cur.fetchone()[0])
        except Exception:
            cur.execute(
                "INSERT INTO estado (cve_pais, estado) VALUES (:p, :n)",
                {"p": pais_id, "n": nombre_clean},
            )
            cur.execute(
                "SELECT cve_estado FROM estado "
                "WHERE cve_pais = :p AND LOWER(TRIM(estado)) = :n "
                "ORDER BY cve_estado DESC FETCH FIRST 1 ROWS ONLY",
                {"p": pais_id, "n": nombre_key},
            )
            row2 = cur.fetchone()
            return int(row2[0]) if row2 else None

    def resolve_or_create_colonia(
        self,
        cp: str,
        nombre: str,
        municipio: str | None = None,
        estado: int | None = None,
        pais: int | None = None,
    ) -> int | None:
        if not nombre or not str(nombre).strip():
            return None

        conn = self._db.get_connection()
        cur = conn.cursor()

        cp_clean = "".join(ch for ch in (cp or "") if str(ch).isdigit())[:5]
        nombre_clean = str(nombre).strip()
        nombre_key = nombre_clean.lower()

        if not cp_clean:
            return None

        cur.execute(
            "SELECT cve_cp FROM cp WHERE cp = :cp FETCH FIRST 1 ROWS ONLY",
            {"cp": cp_clean},
        )
        row = cur.fetchone()
        if row:
            cve_cp = int(row[0])
        else:
            cve_municipio = None
            if municipio and estado:
                cur.execute(
                    "SELECT cve_municipio FROM municipio "
                    "WHERE cve_estado = :e AND LOWER(TRIM(municipio)) = :m "
                    "FETCH FIRST 1 ROWS ONLY",
                    {"e": int(estado), "m": str(municipio).strip().lower()},
                )
                r2 = cur.fetchone()
                if r2:
                    cve_municipio = int(r2[0])

            if cve_municipio is None:
                return None

            cur.execute(
                "INSERT INTO cp (cve_cp, cp, cve_municipio) "
                "VALUES (cp_cve_cp_seq.NEXTVAL, :cp, :mun)",
                {"cp": cp_clean, "mun": cve_municipio},
            )
            cur.execute("SELECT cp_cve_cp_seq.CURRVAL FROM dual")
            cve_cp = int(cur.fetchone()[0])

        cur.execute(
            "SELECT cve_colonia FROM colonia "
            "WHERE cve_cp = :cp AND LOWER(TRIM(colonia)) = :n FETCH FIRST 1 ROWS ONLY",
            {"cp": cve_cp, "n": nombre_key},
        )
        r3 = cur.fetchone()
        if r3:
            return int(r3[0])

        cur.execute(
            "INSERT INTO colonia (cve_colonia, colonia, cve_cp) "
            "VALUES (colonia_cve_colonia_seq.NEXTVAL, :n, :cp)",
            {"n": nombre_clean, "cp": cve_cp},
        )
        cur.execute("SELECT colonia_cve_colonia_seq.CURRVAL FROM dual")
        return int(cur.fetchone()[0])

    # ================ Cliente: helpers y operaciones UI ================
    def cliente_detalle(self, cve_cliente: int) -> dict | None:
        """
        Lee directo desde CLIENTE usando mapeo de columnas para
        devolver solo los campos que usa la UI.
        """
        cmap = self._cliente_colmap()
        if not cmap.get("pk"):
            return None

        select_cols = [cmap[k] for k in ("nombre","paterno","materno","correo","telefono","calle","num_calle") if cmap.get(k)]
        if not select_cols:
            return None

        sql = f"SELECT {', '.join(select_cols)} FROM CLIENTE WHERE {cmap['pk']} = :IDVAL"
        conn = self._db.get_connection()
        cur = conn.cursor()
        cur.execute(sql, {"IDVAL": int(cve_cliente)})
        row = cur.fetchone()
        if not row:
            return None

        keys = [k for k in ("nombre","paterno","materno","correo","telefono","calle","num_calle") if cmap.get(k)]
        return {k: (row[i] if row[i] is not None else "") for i, k in enumerate(keys)}

    def guardar_cliente_de_orden(self, cve_orden: int, *args, **kwargs) -> int | None:
        """
        Inserta/actualiza el cliente vinculado a una orden.
        Acepta posicionales (en este orden):
          [nombre, paterno, materno, correo, telefono, calle, num_calle,
           cp5, colonia, municipio, estado, pais]
        o keywords con esos nombres.
        Devuelve cve_cliente.
        """
        # ------ mapear args -> kwargs ------
        arg_names = [
            "nombre", "paterno", "materno", "correo", "telefono",
            "calle", "num_calle", "cp5", "colonia", "municipio", "estado", "pais",
        ]
        for i, v in enumerate(args):
            if i < len(arg_names) and arg_names[i] not in kwargs:
                kwargs[arg_names[i]] = v

        # normalizar
        nombre   = self._str_clean(kwargs.get("nombre"))
        paterno  = self._str_clean(kwargs.get("paterno"))
        materno  = self._str_clean(kwargs.get("materno"))
        correo   = self._str_clean(kwargs.get("correo"))
        telefono = self._str_clean(kwargs.get("telefono"))
        calle    = self._str_clean(kwargs.get("calle"))
        num_calle= self._str_clean(kwargs.get("num_calle"))
        cp5      = self._str_clean(kwargs.get("cp5"))
        colonia  = self._str_clean(kwargs.get("colonia"))
        municipio= self._str_clean(kwargs.get("municipio"))
        estado   = self._str_clean(kwargs.get("estado"))
        pais     = kwargs.get("pais")

        if not nombre or not paterno:
            raise ValueError("nombre y paterno son obligatorios")

        # buscar cliente ya ligado a la orden
        cve_cliente = self.cliente_id_por_orden(int(cve_orden))

        # upsert estado si nos dieron nombre (pais debe existir)
        cve_estado = None
        if estado:
            cve_estado = self.upsert_estado(pais or 1, estado)

        # (opcional) normalizar colonia/cp
        _ = self.resolve_or_create_colonia(cp5, colonia, municipio, cve_estado, pais) if cp5 and colonia else None

        if cve_cliente:
            # actualizar
            self.actualizar_cliente(
                int(cve_cliente),
                nombre=nombre, paterno=paterno, materno=materno,
                correo=correo, telefono=telefono,
                calle=calle, num_calle=num_calle,
            )
            return int(cve_cliente)

        # insertar y re-vincular a la orden
        new_id = self.insertar_cliente_y_verificar_datos(
            nombre, paterno, materno, correo, telefono,
            calle, num_calle, cp5, colonia, municipio, estado, pais
        )
        conn = self._db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE orden SET cve_cliente = :cli WHERE cve_orden = :ord",
            {"cli": int(new_id), "ord": int(cve_orden)},
        )
        return int(new_id)

    # ============================== Misc ==============================
    @property
    def _connection(self):
        return self._db.get_connection()