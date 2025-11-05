# view/servicios.py
import flet as ft

def open_servicios_dialog(page: ft.Page, db):
    dd = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in db.ordenes()])
    lista = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def actualizar(e=None):
        lista.controls.clear()
        if dd.value:
            for s in db.servicios_orden(int(dd.value)) or []:
                t = f'{s["cve_orden_servicio"]}  ${s.get("precio",0)}\n{s.get("descripcion","")}'
                lista.controls.append(ft.ListTile(title=ft.Text(t)))
        page.update()
    dd.on_change = actualizar

    dlg = ft.AlertDialog(
        title=ft.Text("Servicios por orden"),
        content=ft.Column([dd, ft.Container(lista, height=260, width=540)], width=560, tight=True),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nuevo_servicio_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    dd_ord = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes])
    dd_srv = ft.Dropdown(label="Servicio", options=[ft.dropdown.Option(text=f'{s["cve_servicio"]} ${s["precio"]} {s["descripcion"]}', key=s["cve_servicio"]) for s in db.servicios()])
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd_ord.value or not dd_srv.value:
            err.value = "Seleccione todos los campos"; page.update(); return
        try:
            db.servicio_orden(orden=int(dd_ord.value), servicio=int(dd_srv.value))
            conn.commit()
            close(); page.open(ft.SnackBar(ft.Text("Servicio agregado con éxito")))
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Añadir servicio a orden"),
        content=ft.Column([dd_ord, dd_srv, err], width=560, tight=True),
        actions=[ft.ElevatedButton("Añadir", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()