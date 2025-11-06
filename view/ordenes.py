# view/ordenes.py
from __future__ import annotations
import flet as ft

# Compat Flet (algunos entornos exponen Colors/Icons en vez de colors/icons)
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

# Import del diálogo de cliente (ajusta la ruta si lo tienes en otro lado)
try:
    from view.cliente import open_editar_cliente_dialog
except Exception:
    try:
        from cliente import open_editar_cliente_dialog  # mismo dir
    except Exception:
        open_editar_cliente_dialog = None  # para evitar crash si falta


# ------------------------- Helpers -------------------------
def _call_first_if_present(target, names: list[str], *args, **kwargs):
    """
    Intenta invocar el primer método disponible en 'target' con alguno
    de los nombres dados. Útil para soportar backends con nombres distintos.
    """
    for n in names:
        if hasattr(target, n):
            fn = getattr(target, n)
            try:
                return True, fn(*args, **kwargs), n
            except TypeError:
                try:
                    return True, fn(**kwargs), n
                except Exception:
                    pass
            except Exception:
                pass
    return False, None, None


def _status_catalog(db_instance) -> dict[int, str]:
    """
    Devuelve {id:int -> nombre:str}. Si falla, usa fallback.
    """
    try:
        raw = db_instance.statuses() or {}
    except Exception:
        raw = {}

    cat: dict[int, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                cat[int(str(k).strip())] = str(v or "").strip()
            except Exception:
                pass
        if cat:
            return cat

    for it in (raw or []):
        if isinstance(it, dict):
            k = it.get("cve_status") or it.get("id") or it.get("cve")
            v = it.get("descripcion") or it.get("nombre") or it.get("status")
        else:
            try:
                k, v = it[0], it[1]
            except Exception:
                continue
        try:
            k = int(str(k).strip())
        except Exception:
            continue
        cat[k] = str(v or "").strip()

    return cat or {1: "En proceso", 2: "Terminado", 3: "Recogido"}


def _tipo_text(v) -> str:
    """
    Extrae el texto de un item de tipos (tolera lista/tupla/dict/str).
    Esperado: {id: (tarifa, nombre)} o {id: {"descripcion": "...", "nombre": "..."}}
    """
    if isinstance(v, (list, tuple)):
        # cuando viene de DBFacade.tipos(): (tarifa, nombre)
        return str(v[1] if len(v) > 1 else v[0])
    if isinstance(v, dict):
        return str(v.get("descripcion") or v.get("nombre") or v.get("tipo") or "")
    return str(v or "")


# ------------------- Ver técnicos del taller -------------------
def open_tecnicos_taller_dialog(page: ft.Page, db_instance, connection, orden_obj, on_saved=None):
    """
    Lista técnicos del taller asignado a la orden (solo lectura).
    """
    cve_taller = getattr(orden_obj, "cve_taller", None)
    tecnicos = []
    try:
        if cve_taller is not None:
            tecnicos = db_instance.tecnicos_taller(cve_taller) or []
    except Exception:
        tecnicos = []

    lista = ft.Column(
        controls=[
            ft.ListTile(title=ft.Text(f"{t.get('nombre','')} {t.get('paterno','')}".strip()))
            for t in tecnicos if isinstance(t, dict)
        ] or [ft.Text("Sin técnicos disponibles")],
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )

    def cerrar(_=None):
        page.dialog.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Técnicos del Taller #{cve_taller}"),
        content=lista,
        actions=[ft.TextButton("Cerrar", on_click=cerrar)],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=18),
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


# --------------------- Editar una orden ----------------------
def open_editar_orden_dialog(
    page: ft.Page,
    db_instance,
    orden_obj,
    on_saved=None,
    connection=None,
):
    """
    Diálogo de edición de orden:
      - Marca, Modelo
      - Tipo (catálogo de tipos)
      - Status (catálogo de status)
      - Nota del cliente
      - Taller / Técnico
    """

    # Getter flexible para dict/objeto
    def gv(o, *keys, default=None):
        if isinstance(o, dict):
            for k in keys:
                if k in o:
                    return o[k]
        for k in keys:
            if hasattr(o, k):
                return getattr(o, k)
        return default

    cve_orden = gv(orden_obj, "cve_orden", "orden", "id", default=None)
    if cve_orden is None:
        page.open(ft.SnackBar(ft.Text("No se pudo identificar la orden.")))
        return

    # --- catálogos ---
    status_cat = _status_catalog(db_instance)     # {id: nombre}
    tipos_cat  = db_instance.tipos() or {}        # {id: (tarifa, nombre) | dict | str}
    talls_cat  = db_instance.talleres() or {}     # {id: nombre}

    # --- campos ---
    dd_status = ft.Dropdown(
        label="Estatus",
        options=[ft.dropdown.Option(text=v, key=k) for k, v in status_cat.items()],
        value=gv(orden_obj, "cve_status"),
        expand=True,
    )

    tf_marca  = ft.TextField(label="Marca", value=str(gv(orden_obj, "eq_marca", default="") or ""), expand=True)
    tf_modelo = ft.TextField(label="Modelo", value=str(gv(orden_obj, "eq_modelo", default="") or ""), expand=True)
    dd_tipo   = ft.Dropdown(
        label="Tipo",
        options=[ft.dropdown.Option(text=_tipo_text(v), key=k) for k, v in tipos_cat.items()],
        value=gv(orden_obj, "cve_tipo_equipo"),
        expand=True,
    )
    tf_nota   = ft.TextField(
        label="Nota del cliente",
        value=str(gv(orden_obj, "notas_cliente", default="") or ""),
        multiline=True,
        expand=True,
    )

    dd_taller = ft.Dropdown(
        label="Taller",
        options=[ft.dropdown.Option(text=str(v), key=int(k)) for k, v in talls_cat.items()],
        value=gv(orden_obj, "cve_taller"),
        expand=True,
    )
    dd_tecnico = ft.Dropdown(label="Técnico", options=[], expand=True, disabled=True)

    def _cargar_tecnicos(_=None):
        dd_tecnico.disabled = True
        dd_tecnico.options = []
        if dd_taller.value:
            try:
                tecs = db_instance.tecnicos_taller(dd_taller.value) or []
            except Exception:
                tecs = []
            dd_tecnico.options = [
                ft.dropdown.Option(
                    text=f"{t.get('nombre','')} {t.get('paterno','')}".strip(),
                    key=t.get("cve_empleado"),
                )
                for t in tecs if isinstance(t, dict)
            ]
            dd_tecnico.disabled = False
            dd_tecnico.value = gv(orden_obj, "cve_tecnico")
        page.update()

    dd_taller.on_change = _cargar_tecnicos
    _cargar_tecnicos()

    error_lbl = ft.Text("", color=ft.colors.RED_300)

    # --- acciones ---
    def cerrar(_=None):
        page.dialog.open = False
        page.update()

    def _commit_safely():
        # usa connection explícito si te lo pasan; si no, pide a la fachada.
        conn = connection
        if conn is None and hasattr(db_instance, "get_connection"):
            try:
                conn = db_instance.get_connection()
            except Exception:
                conn = None
        if conn:
            try:
                conn.commit()
            except Exception:
                pass

    def _rollback_safely():
        conn = connection
        if conn is None and hasattr(db_instance, "get_connection"):
            try:
                conn = db_instance.get_connection()
            except Exception:
                conn = None
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

    def guardar(_=None):
        error_lbl.value = ""
        page.update()

        if not all([dd_status.value, dd_tipo.value, dd_taller.value]):
            error_lbl.value = "Seleccione estatus, tipo y taller."
            page.update()
            return

        payload = dict(
            cve_orden=cve_orden,
            cve_status=int(dd_status.value),
            eq_marca=(tf_marca.value or "").strip(),
            eq_modelo=(tf_modelo.value or "").strip(),
            cve_tipo_equipo=int(dd_tipo.value),
            notas_cliente=(tf_nota.value or "").strip(),
            cve_taller=int(dd_taller.value),
            cve_tecnico=int(dd_tecnico.value) if dd_tecnico.value else None,
        )

        # Nombre flexible del método en la fachada / controlador
        CANDIDATE_METHODS = [
            "actualizar_orden",
            "update_orden",
            "editar_orden",
            "orden_update",
            "orden_actualizar",
            "actualizar",          # por si se llama directo al controlador
            "update",
        ]

        ok, _res, _used = _call_first_if_present(db_instance, CANDIDATE_METHODS, **payload)
        if not ok and hasattr(db_instance, "_orden"):
            ok, _res, _used = _call_first_if_present(getattr(db_instance, "_orden"), CANDIDATE_METHODS, **payload)

        if ok:
            _commit_safely()
            page.open(ft.SnackBar(ft.Text(f"Orden #{cve_orden} actualizada")))
            try:
                if callable(on_saved):
                    on_saved()
            finally:
                cerrar()
        else:
            _rollback_safely()
            error_lbl.value = "No se encontró método para actualizar la orden en el backend."
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Editar Orden #{cve_orden}", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            [
                error_lbl,
                ft.Row([dd_status]),
                ft.Row([tf_marca, tf_modelo, dd_tipo]),
                tf_nota,
                ft.Row([dd_taller, dd_tecnico]),
            ],
            spacing=8,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar),
            ft.FilledButton("Guardar", icon=ft.icons.SAVE, on_click=guardar),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=18),  # ← corregido (antes Rxounded)
    )

    page.dialog = dlg
    dlg.open = True
    page.update()


# --------------------- Vista de Órdenes + Editar Cliente ----------------------
def open_ordenes_page(page: ft.Page, db_instance):
    """
    Lista de órdenes con botón para 'Editar cliente' (precargado)
    y botón para 'Editar orden'.
    """
    tabla = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def gv(o, *keys, default=None):
        if isinstance(o, dict):
            for k in keys:
                if k in o:
                    return o[k]
        for k in keys:
            if hasattr(o, k):
                return getattr(o, k)
        return default

    def recargar_tabla(_=None):
        tabla.controls.clear()
        try:
            ordenes = db_instance.ordenes() or []
        except Exception:
            ordenes = []

        for o in ordenes:
            cve_orden = gv(o, "cve_orden", "orden", "id")
            status    = gv(o, "status", "estatus", default="")
            tecnico   = gv(o, "tecnico", "empleado", default="")
            cliente   = gv(o, "cliente", "nombre_cliente", default="")
            modelo    = gv(o, "eq_modelo", "modelo", default="")
            marca     = gv(o, "eq_marca", "marca", default="")

            btn_editar_cliente = ft.IconButton(
                icon=ft.icons.PERSON,
                tooltip="Editar cliente (precargado)",
                on_click=lambda e, orden=o: _editar_cliente_desde_orden(orden),
            )
            btn_editar_orden = ft.IconButton(
                icon=ft.icons.EDIT,
                tooltip="Editar orden",
                on_click=lambda e, orden=o: open_editar_orden_dialog(page, db_instance, orden, on_saved=recargar_tabla),
            )

            fila = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(f"#{cve_orden}", width=80),
                    ft.Text(str(status), width=120),
                    ft.Text(str(tecnico), width=200),
                    ft.Text(str(cliente), width=220),
                    ft.Text(str(marca), width=160),
                    ft.Text(str(modelo), width=160),
                    ft.Row([btn_editar_cliente, btn_editar_orden]),
                ],
            )
            tabla.controls.append(fila)

        page.update()

    def _editar_cliente_desde_orden(orden_obj):
        if open_editar_cliente_dialog is None:
            page.open(ft.SnackBar(ft.Text("No se pudo cargar el diálogo de cliente (import).")))
            return

        cve_orden = gv(orden_obj, "cve_orden", "orden", "id")
        if not cve_orden:
            page.open(ft.SnackBar(ft.Text("No se pudo identificar la orden.")))
            return

        try:
            cve_cliente = db_instance.cliente_id_por_orden(int(cve_orden))
        except Exception:
            cve_cliente = None

        if not cve_cliente:
            page.open(ft.SnackBar(ft.Text("La orden no tiene cliente ligado.")))
            return

        try:
            cliente_det = db_instance.cliente_detalle(int(cve_cliente)) or {}
        except Exception:
            cliente_det = {}

        open_editar_cliente_dialog(page, db_instance, cliente_det, cve_orden, on_saved=recargar_tabla)

    # Render
    page.controls.clear()
    page.add(
        ft.Column(
            controls=[
                ft.Text("Órdenes", size=22, weight=ft.FontWeight.BOLD),
                tabla,
            ],
            expand=True,
        )
    )
    recargar_tabla()