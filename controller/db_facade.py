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
    def __init__(self, hostname: str, port: str, service_name: str, username: str, password: str):
        self._db = OracleDB(
            hostname=hostname, port=port, service_name=service_name,
            username=username, password=password
        )

        # Modelos
        om = OrdenModelo(self._db)
        nm = NotaModelo(self._db)
        pm = ParteModelo(self._db)
        sm = ServicioModelo(self._db)
        cm = ClienteModelo(self._db)
        catm = CatalogosModelo(self._db)

        # Controladores
        self._orden = OrdenControlador(om)
        self._nota = NotaControlador(nm)
        self._parte = ParteControlador(pm)
        self._servicio = ServicioControlador(sm)
        self._cliente = ClienteControlador(cm)
        self._catalogos = CatalogosControlador(catm)

    # -------- helpers internos --------
    def _coerce_int(self, v):
        try:
            if v is None:
                return None
            s = str(v).strip()
            if s == "":
                return None
            return int(s)
        except Exception:
            return v

    def _coerce_client_id(self, v):
        """Acepta int / str / dict / tuple(list) y devuelve el id de cliente como int."""
        if isinstance(v, int):
            return v
        if v is None:
            return None
        s = str(v).strip()
        if s.isdigit():
            return int(s)
        if isinstance(v, dict):
            for k in ("cve_cliente", "cliente", "id", "cve"):
                val = v.get(k)
                if val is not None and str(val).strip().isdigit():
                    return int(val)
        if isinstance(v, (list, tuple)) and len(v) > 0:
            try:
                return int(v[0])
            except Exception:
                pass
        return v

    def _resolve_id_from_catalog(self, value, items, id_keys=('id', 'cve', 'cve_id'),
                                 text_keys=('descripcion', 'nombre', 'desc', 'texto', 'label', 'tipo', 'taller', 'tecnico')):
        """Mapea texto → id usando un catálogo; también admite items como tuplas (id, texto, ...)."""
        vi = self._coerce_int(value)
        if isinstance(vi, int):
            return vi

        s = ("" if value is None else str(value)).strip()
        if s == "":
            return None

        def _get(it, k):
            if isinstance(it, dict):
                return it.get(k)
            if isinstance(it, (list, tuple)):
                # Asumimos (id, texto, ...)
                if k in id_keys:
                    return it[0] if len(it) > 0 else None
                return it[1] if len(it) > 1 else None
            return getattr(it, k, None)

        for it in items or []:
            for tk in text_keys:
                tv = _get(it, tk)
                if tv is None:
                    continue
                if str(tv).strip().lower() == s.lower():
                    for ik in id_keys:
                        iv = _get(it, ik)
                        if iv is not None:
                            try:
                                return int(iv)
                            except Exception:
                                pass
        return value

    # -------- compatibilidad para clases que esperan OracleDB --------
    @property
    def _connection(self):
        """Permite que clases del modelo que esperan 'db_instance._connection' funcionen con el Facade."""
        return self._db.get_connection()

    # -------- conexión --------
    def get_connection(self):
        return self._db.get_connection()

    def close_connection(self):
        return self._db.close_connection()

    # -------- Órdenes --------
    def ordenes(self):
        return self._orden.listar()

    def insertar_orden(self, *args, **kwargs):
        """
        Firma esperada por OracleDB.insertar_orden:
        (cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente, cve_taller, cve_tecnico)
        Convertimos a int y mapeamos texto→id para tipo/taller/técnico/cliente.
        """
        if args and not kwargs:
            keys = ["cve_status", "eq_marca", "eq_modelo", "cve_tipo_equipo",
                    "notas_cliente", "cliente", "cve_taller", "cve_tecnico"]
            kwargs = {k: (args[i] if i < len(args) else None) for i, k in enumerate(keys)}

        # status → int
        kwargs["cve_status"] = self._coerce_int(kwargs.get("cve_status"))

        # tipo
        kwargs["cve_tipo_equipo"] = self._resolve_id_from_catalog(
            kwargs.get("cve_tipo_equipo"),
            self._catalogos.tipos(),
            id_keys=("cve_tipo_equipo", "id", "cve"),
            text_keys=("descripcion", "nombre", "tipo"),
        )

        # taller
        kwargs["cve_taller"] = self._resolve_id_from_catalog(
            kwargs.get("cve_taller"),
            self._catalogos.talleres(),
            id_keys=("cve_taller", "id", "cve"),
            text_keys=("nombre", "descripcion", "taller"),
        )

        # técnico (si viene texto, buscar en técnicos del taller)
        tec_raw = kwargs.get("cve_tecnico")
        tec_res = self._coerce_int(tec_raw)
        if not isinstance(tec_res, int):
            taller_id = self._coerce_int(kwargs.get("cve_taller"))
            try:
                tecnicos = self._catalogos.tecnicos_taller(taller_id) if taller_id else []
            except Exception:
                tecnicos = []
            tec_res = self._resolve_id_from_catalog(
                tec_raw, tecnicos,
                id_keys=("cve_tecnico", "id", "cve"),
                text_keys=("nombre", "tecnico", "descripcion"),
            )
        kwargs["cve_tecnico"] = tec_res

        # cliente
        kwargs["cliente"] = self._coerce_client_id(kwargs.get("cliente"))

        return self._orden.insertar(
            kwargs.get("cve_status"),
            kwargs.get("eq_marca"),
            kwargs.get("eq_modelo"),
            kwargs.get("cve_tipo_equipo"),
            kwargs.get("notas_cliente"),
            kwargs.get("cliente"),
            kwargs.get("cve_taller"),
            kwargs.get("cve_tecnico"),
        )

    def tecnicos_orden(self, cve_orden, horas=False):
        return self._orden.tecnicos_orden(cve_orden, horas)

    # -------- Notas --------
    def notas(self, cve_orden):
        return self._nota.listar(cve_orden)

    def insertar_nota(self, cve_orden, nota):
        return self._nota.insertar(cve_orden, nota)

    def eliminar_nota(self, cve_nota):
        return self._nota.eliminar(cve_nota)

    # -------- Partes (catálogo y por orden) --------
    def partes(self):
        return self._parte.catalogo()

    def partes_orden(self, cve_orden):
        return self._parte.listar(cve_orden)

    def parte_orden(self, *args, **kwargs):
        if args and len(args) >= 2:
            return self._parte.insertar(self._coerce_int(args[0]), self._coerce_int(args[1]))
        cve_orden = kwargs.get("cve_orden") or kwargs.get("orden") or kwargs.get("id_orden")
        parte_id  = kwargs.get("parte_id")  or kwargs.get("cve_parte") or kwargs.get("parte")
        return self._parte.insertar(self._coerce_int(cve_orden), self._coerce_int(parte_id))

    def eliminar_parte(self, cve_parte_orden):
        return self._parte.eliminar(cve_parte_orden)

    # -------- Servicios (catálogo y por orden) --------
    def servicios(self):
        return self._servicio.catalogo()

    def servicios_orden(self, cve_orden):
        return self._servicio.listar(cve_orden)

    def servicio_orden(self, *args, **kwargs):
        if args and len(args) >= 2:
            return self._servicio.insertar(self._coerce_int(args[0]), self._coerce_int(args[1]))
        cve_orden   = kwargs.get("cve_orden")   or kwargs.get("orden")    or kwargs.get("id_orden")
        servicio_id = kwargs.get("servicio_id") or kwargs.get("cve_servicio") or kwargs.get("servicio")
        return self._servicio.insertar(self._coerce_int(cve_orden), self._coerce_int(servicio_id))

    def eliminar_servicio(self, cve_servicio_orden):
        return self._servicio.eliminar(cve_servicio_orden)

    # -------- Cliente --------
    def insertar_cliente_y_verificar_datos(self, *args, **kwargs):
        return self._cliente.insertar_y_verificar(*args, **kwargs)

    # -------- Catálogos --------
    def tipos(self):
        return self._catalogos.tipos()

    def estados(self, pais):
        return self._catalogos.estados(pais)

    def paises(self):
        return self._catalogos.paises()

    def talleres(self):
        return self._catalogos.talleres()

    def tecnicos_taller(self, cve_taller):
        return self._catalogos.tecnicos_taller(cve_taller)
    @property
    def _connection(self):
        return self._db.get_connection()