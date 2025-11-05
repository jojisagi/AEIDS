# view/partes.py
import flet as ft

def open_partes_dialog(page: ft.Page, db):
    dd = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in db.ordenes()])
    lista = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def actualizar(e=None):
        lista.controls.clear()
        if dd.value:
            for p in db.partes_orden(int(dd.value)) or []:
                t = f'{p["cve_orden_parte"]}  {(p.get("part_no") or "")}  ${p.get("precio",0)}\n{p.get("descripcion","")}'
                lista.controls.append(ft.ListTile(title=ft.Text(t)))
        page.update()
    dd.on_change = actualizar

    dlg = ft.AlertDialog(
        title=ft.Text("Partes por orden"),
        content=ft.Column([dd, ft.Container(lista, height=260, width=540)], width=560, tight=True),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nueva_parte_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    dd_ord = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes])
    dd_par = ft.Dropdown(label="Pieza", options=[ft.dropdown.Option(text=f'{p["cve_parte"]} {(p["part_no"] or "")} {p["descripcion"]} ${p["precio"]}', key=p["cve_parte"]) for p in db.partes()])
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd_ord.value or not dd_par.value:
            err.value = "Seleccione todos los campos"; page.update(); return
        try:
            db.parte_orden(orden=int(dd_ord.value), parte=int(dd_par.value))
            conn.commit()
            close(); page.open(ft.SnackBar(ft.Text("Parte agregada con éxito")))
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Añadir parte a orden"),
        content=ft.Column([dd_ord, dd_par, err], width=560, tight=True),
        actions=[ft.ElevatedButton("Añadir", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()