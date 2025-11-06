# view/orden.py
from __future__ import annotations
import flet as ft

# Compat Flet
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons


def open_editar_orden_dialog(
    page: ft.Page,
    db_instance,
    connection,
    orden_obj: dict | object,
    on_saved: callable | None = None,
):
    """
    Diálogo para editar una orden:
      - status
      - marca/modelo
      - tipo (catálogo)
      - nota del cliente
      - taller / técnico
    `orden_obj` puede ser dict u objeto con atributos:
    cve_orden, cve_status, eq_marca, eq_modelo, cve_tipo_equipo,
    notas_cliente, cve_taller, cve_tecnico
    """

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

    # --------- catálogos ---------
    status_cat = db_instance.statuses() or {}             # {id: nombre}
    tipos_cat  = db_instance.tipos() or {}                # {id: (tarifa, nombre)}
    talls_cat  = db_instance.talleres() or {}             # {id: nombre}

    # --------- campos ---------
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
        options=[ft.dropdown.Option(text=v[1], key=k) for k, v in tipos_cat.items()],
        value=gv(orden_obj, "cve_tipo_equipo"),
        expand=True,
    )
    tf_nota   = ft.TextField(label="Nota del cliente", value=str(gv(orden_obj, "notas_cliente", default="") or ""),
                             multiline=True, expand=True)

    dd_taller = ft.Dropdown(
        label="Taller",
        options=[ft.dropdown.Option(text=v, key=k) for k, v in talls_cat.items()],
        value=gv(orden_obj, "cve_taller"),
        expand=True,
    )
    dd_tecnico = ft.Dropdown(label="Técnico", options=[], expand=True, disabled=True)

    def _cargar_tecnicos(e=None):
        dd_tecnico.disabled = True
        dd_tecnico.options = []
        if dd_taller.value:
            try:
                tecs = db_instance.tecnicos_taller(dd_taller.value) or []
            except Exception:
                tecs = []
            dd_tecnico.options = [
                ft.dropdown.Option(text=f"{t.get('nombre','')} {t.get('paterno','')}".strip(),
                                   key=t.get('cve_empleado')) for t in tecs
            ]
            dd_tecnico.disabled = False
            # intenta seleccionar el ya asignado
            dd_tecnico.value = gv(orden_obj, "cve_tecnico")
        page.update()

    dd_taller.on_change = _cargar_tecnicos
    _cargar_tecnicos()

    error_lbl = ft.Text("", color=ft.colors.RED_300)

    # --------- acciones ---------
    dlg = ft.AlertDialog(modal=True)

    def cerrar(_=None):
        dlg.open = False
        page.update()

    def guardar(_=None):
        error_lbl.value = ""
        page.update()

        if not all([dd_status.value, dd_tipo.value, dd_taller.value]):
            error_lbl.value = "Seleccione estatus, tipo y taller."
            page.update(); return

        try:
            db_instance.actualizar_orden(
                cve_orden=cve_orden,
                cve_status=dd_status.value,
                eq_marca=tf_marca.value.strip(),
                eq_modelo=tf_modelo.value.strip(),
                cve_tipo_equipo=dd_tipo.value,
                notas_cliente=tf_nota.value.strip(),
                cve_taller=dd_taller.value,
                cve_tecnico=dd_tecnico.value,
            )
            try:
                connection.commit()
            except Exception:
                pass

            page.open(ft.SnackBar(ft.Text(f"Orden #{cve_orden} actualizada")))
            if callable(on_saved):
                try: on_saved()
                except Exception: pass
            cerrar()

        except Exception as ex:
            try:
                connection.rollback()
            except Exception:
                pass
            error_lbl.value = f"Error al actualizar: {ex}"
            page.update()

    dlg.title = ft.Text(f"Editar orden #{cve_orden}", weight=ft.FontWeight.BOLD)
    dlg.content = ft.Container(
        width=720,
        content=ft.Column(
            [
                error_lbl,
                ft.Row([dd_status]),
                ft.Row([tf_marca, tf_modelo, dd_tipo]),
                tf_nota,
                ft.Row([dd_taller, dd_tecnico]),
            ],
            spacing=8, tight=True
        ),
    )
    dlg.actions = [
        ft.TextButton("Cancelar", on_click=cerrar),
        ft.FilledButton("Guardar", icon=ft.icons.SAVE, on_click=guardar),
    ]

    page.dialog = dlg
    dlg.open = True
    page.update()