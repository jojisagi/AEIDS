# view/servicios.py
import flet as ft

if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors

def open_servicios_dialog(page: ft.Page, db):
    cont = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=520)
    dd = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in (db.ordenes() or [])],
        width=520
    )

    def fila(s):
        txt = f"{s.get('cve_orden_servicio')}#  ${s.get('precio',0)}\n{s.get('descripcion','')}"
        return ft.ListTile(title=ft.Text(txt))

    def actualizar(e=None):
        cont.controls.clear()
        if dd.value:
            for s in db.servicios_orden(dd.value):
                cont.controls.append(fila(s))
        page.update()

    dd.on_change = actualizar
    dlg = ft.AlertDialog(
        title=ft.Text("Ver servicios"),
        content=ft.Column([dd, ft.Container(cont, height=260, width=540)], tight=True, width=560),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nuevo_servicio_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    if not ordenes:
        page.open(ft.SnackBar(ft.Text("No hay órdenes para agregar servicios.")))
        return
    dd_ord = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes],
        value=ordenes[0].cve_orden, width=540
    )
    dd_srv = ft.Dropdown(
        label="Servicio",
        options=[ft.dropdown.Option(text=f"{s['cve_servicio']} ${s['precio']} {s['descripcion']}",
                                    key=s["cve_servicio"]) for s in db.servicios()],
        width=540
    )
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd_ord.value or not dd_srv.value:
            err.value = "Seleccione todos los campos"; page.update(); return
        try:
            db.servicio_orden(orden=dd_ord.value, servicio=dd_srv.value)
            conn.commit()
            close()
            page.open(ft.SnackBar(ft.Text("Servicio agregado con éxito")))
            open_servicios_dialog(page, db)
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Añadir servicio a orden"),
        content=ft.Column([dd_ord, dd_srv, err], tight=True, width=560),
        actions=[ft.ElevatedButton("Añadir", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()

# Aliases
open_services_dialog = open_servicios_dialog
open_new_service_dialog = open_nuevo_servicio_dialog