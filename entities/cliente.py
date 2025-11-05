# view/cliente.py
from __future__ import annotations
import re
import flet as ft

# Compatibilidad Flet
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
PHONE_10_RE = re.compile(r"^\d{10}$")
PHONE_PLUS52_RE = re.compile(r"^\+52\d{10}$")
HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)

def _normalize_house(s: str) -> str:
    s = (s or "").strip().upper().replace(" ", "")
    s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
    if s in ("SN", "S-N"):
        s = "S/N"
    return s

def _normalize_phone(s: str) -> str | None:
    s = (s or "").strip()
    if PHONE_10_RE.fullmatch(s):
        return s
    if PHONE_PLUS52_RE.fullmatch(s):
        return s[-10:]
    return None


def open_editar_cliente_dialog(
    page: ft.Page,
    db_instance,
    cliente_ref: dict | object | str | int | None,
    cve_orden: int | None = None,
    on_saved: callable | None = None,
):
    """
    Dialog para editar un cliente. `cliente_ref` puede ser:
      - id de cliente
      - dict/objeto con campos
      - string (ignoramos y tratamos de leer por `cve_orden`)
    Si se proporciona `cve_orden`, intentamos leer el cliente de la orden.
    """
    # --------- Cargar datos actuales ----------
    detalle = None
    if cve_orden is not None:
        try:
            detalle = db_instance.cliente_de_orden(int(cve_orden))
        except Exception:
            detalle = None

    if detalle is None and cliente_ref is not None:
        if isinstance(cliente_ref, int) or (isinstance(cliente_ref, str) and cliente_ref.isdigit()):
            detalle = db_instance.cliente_por_id(int(cliente_ref))
        elif isinstance(cliente_ref, dict):
            detalle = cliente_ref
        else:
            # objeto con atributos comunes
            detalle = {
                "cve_cliente": getattr(cliente_ref, "cve_cliente", None),
                "nombre": getattr(cliente_ref, "nombre", ""),
                "paterno": getattr(cliente_ref, "paterno", ""),
                "materno": getattr(cliente_ref, "materno", ""),
                "correo": getattr(cliente_ref, "correo", ""),
                "telefono": getattr(cliente_ref, "telefono", ""),
                "calle": getattr(cliente_ref, "calle", ""),
                "numero": getattr(cliente_ref, "numero", ""),
                "cp": getattr(cliente_ref, "cp", ""),
                "colonia": getattr(cliente_ref, "colonia", ""),
                "municipio": getattr(cliente_ref, "municipio", ""),
                "estado": getattr(cliente_ref, "estado", ""),
                "pais": getattr(cliente_ref, "pais", ""),
            }

    if detalle is None:
        page.open(ft.SnackBar(ft.Text("No fue posible obtener los datos del cliente.")))
        return

    # extrae valores con tolerancia
    def gv(d, *keys, default=""):
        if isinstance(d, dict):
            for k in keys:
                if k in d:
                    return d[k]
        for k in keys:
            if hasattr(d, k):
                return getattr(d, k)
        return default

    cve_cliente = gv(detalle, "cve_cliente", "id", "cliente")

    # --------- Controles ----------
    tf_nombre = ft.TextField(label="Nombre", value=str(gv(detalle, "nombre")), expand=True)
    tf_paterno = ft.TextField(label="Apellido paterno", value=str(gv(detalle, "paterno", "apellido_paterno")), expand=True)
    tf_materno = ft.TextField(label="Apellido materno", value=str(gv(detalle, "materno", "apellido_materno")), expand=True)
    tf_correo  = ft.TextField(label="Correo", value=str(gv(detalle, "correo", "email")), expand=True)
    tf_tel     = ft.TextField(label="Teléfono (10 dígitos o +52...)", value=str(gv(detalle, "telefono", "tel")), expand=True)

    tf_calle   = ft.TextField(label="Calle", value=str(gv(detalle, "calle", "dir_calle")), expand=True)
    tf_numero  = ft.TextField(label="Número", value=str(gv(detalle, "numero", "dir_numero")), expand=True)
    tf_cp      = ft.TextField(label="CP (máx 5 dígitos)", value=str(gv(detalle, "cp", "codigo_postal")), expand=True)
    tf_colonia = ft.TextField(label="Colonia", value=str(gv(detalle, "colonia", "dir_colonia")), expand=True)
    tf_mpio    = ft.TextField(label="Municipio", value=str(gv(detalle, "municipio")), expand=True)

    # País/Estado como catálogos (con "Otro")
    paises = db_instance.paises() or {}
    dd_pais = ft.Dropdown(
        label="País",
        options=[ft.dropdown.Option(text=nombre, key=paises[nombre]) for nombre in paises.keys()],
        expand=True,
    )
    # selecciona país si venía algo
    pais_actual = gv(detalle, "pais")
    if str(pais_actual).strip().isdigit():
        dd_pais.value = int(pais_actual)
    else:
        # buscar por nombre
        inv = {str(k).strip().lower(): v for k, v in paises.items()}
        dd_pais.value = inv.get(str(pais_actual).strip().lower())

    dd_estado = ft.Dropdown(label="Estado", expand=True, disabled=True)
    tf_estado_otro = ft.TextField(label="Otro estado", visible=False, expand=True)

    def _cargar_estados(e=None):
        dd_estado.disabled = True
        dd_estado.options = []
        tf_estado_otro.visible = False
        if dd_pais.value:
            try:
                ests = db_instance.estados(dd_pais.value) or {}
                dd_estado.options = [ft.dropdown.Option(text=n, key=ests[n]) for n in ests.keys()]
                dd_estado.options.insert(0, ft.dropdown.Option("Otro"))
                dd_estado.disabled = False
            except Exception:
                pass
        page.update()

    def _estado_cambio(e=None):
        tf_estado_otro.visible = (dd_estado.value == "Otro")
        page.update()

    dd_pais.on_change = _cargar_estados
    dd_estado.on_change = _estado_cambio
    _cargar_estados()

    # intenta seleccionar estado actual
    estado_actual = gv(detalle, "estado")
    if str(estado_actual).strip().isdigit():
        dd_estado.value = int(estado_actual)
    elif estado_actual:
        # por nombre
        try:
            ests = db_instance.estados(dd_pais.value) or {}
            inv = {str(k).strip().lower(): v for k, v in ests.items()}
            dd_estado.value = inv.get(str(estado_actual).strip().lower())
            if dd_estado.value is None:
                dd_estado.value = "Otro"
                tf_estado_otro.value = str(estado_actual)
                tf_estado_otro.visible = True
        except Exception:
            pass

    error_lbl = ft.Text("", color=ft.colors.RED_300)

    # --------- Validaciones live ----------
    def _cp_live(e=None):
        tf_cp.value = "".join(ch for ch in (tf_cp.value or "") if ch.isdigit())[:5]
        page.update()

    def _num_live(e=None):
        tf_numero.value = _normalize_house(tf_numero.value)
        ok = bool(tf_numero.value and HOUSE_RE.match(tf_numero.value))
        tf_numero.error_text = None if ok else "1–6 dígitos, opcional letra o 'S/N'"
        page.update()

    tf_cp.on_change = _cp_live
    tf_numero.on_change = _num_live

    # --------- Acciones ----------
    dlg = ft.AlertDialog(modal=True)

    def cerrar(_=None):
        dlg.open = False
        page.update()

    def guardar(_=None):
        error_lbl.value = ""
        page.update()

        # mínimos obligatorios
        oblig = [tf_nombre.value, tf_paterno.value, tf_correo.value, tf_tel.value,
                 tf_calle.value, tf_numero.value, tf_cp.value, tf_colonia.value,
                 tf_mpio.value, dd_pais.value]
        if not all(oblig):
            error_lbl.value = "Complete los campos obligatorios."
            page.update()
            return

        # correo / teléfono / número / cp
        if not EMAIL_RE.match((tf_correo.value or "").strip()):
            error_lbl.value = "Correo no válido."
            page.update(); return

        tel_norm = _normalize_phone(tf_tel.value)
        if not tel_norm:
            error_lbl.value = "Teléfono inválido: 10 dígitos o +52 y 10 dígitos."
            page.update(); return

        num_ok = HOUSE_RE.match(_normalize_house(tf_numero.value))
        if not num_ok:
            error_lbl.value = "Número inválido (1–6 dígitos, opcional letra o 'S/N')."
            page.update(); return

        cp = "".join(ch for ch in (tf_cp.value or "") if ch.isdigit())[:5]
        if not cp:
            error_lbl.value = "Capture al menos 1 dígito de CP (máx. 5)."
            page.update(); return

        # estado final
        est_final = tf_estado_otro.value.strip() if dd_estado.value == "Otro" else dd_estado.value
        if not est_final:
            error_lbl.value = "Seleccione un estado o escriba uno."
            page.update(); return

        # resolver/crear colonia (si tu backend necesita id)
        colonia_val = tf_colonia.value.strip()
        try:
            cid = db_instance.resolve_or_create_colonia(
                cp=cp, nombre=colonia_val, municipio=tf_mpio.value.strip(), estado=est_final
            )
            if cid:
                colonia_val = int(cid)
        except Exception:
            pass  # si no se puede, se manda el texto

        try:
            db_instance.actualizar_cliente(
                cve_cliente=cve_cliente,
                nombre=tf_nombre.value.strip(),
                paterno=tf_paterno.value.strip(),
                materno=tf_materno.value.strip(),
                correo=tf_correo.value.strip(),
                telefono=tel_norm,
                calle=tf_calle.value.strip(),
                numero=_normalize_house(tf_numero.value),
                cp=cp,
                colonia=colonia_val,
                municipio=tf_mpio.value.strip(),
                estado=est_final,
                pais=dd_pais.value,
            )
            try:
                db_instance.get_connection().commit()
            except Exception:
                pass

            page.open(ft.SnackBar(ft.Text("Cliente actualizado")))
            if callable(on_saved):
                try: on_saved()
                except Exception: pass
            cerrar()

        except Exception as ex:
            try:
                db_instance.get_connection().rollback()
            except Exception:
                pass
            error_lbl.value = f"Error al actualizar: {ex}"
            page.update()

    dlg.title = ft.Text("Editar cliente", weight=ft.FontWeight.BOLD)
    dlg.content = ft.Container(
        content=ft.Column(
            [
                error_lbl,
                ft.Row([tf_nombre, tf_paterno, tf_materno]),
                ft.Row([tf_correo, tf_tel]),
                ft.Row([tf_calle, tf_numero, tf_cp]),
                ft.Row([tf_colonia, tf_mpio]),
                ft.Row([dd_pais, dd_estado, tf_estado_otro]),
            ],
            tight=True, spacing=8
        ),
        width=720,
    )
    dlg.actions = [
        ft.TextButton("Cancelar", on_click=cerrar),
        ft.FilledButton("Guardar", icon=ft.icons.SAVE, on_click=guardar),
    ]

    page.dialog = dlg
    dlg.open = True
    page.update()