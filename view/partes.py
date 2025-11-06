# view/partes.py
import flet as ft

if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors

def open_partes_dialog(page: ft.Page, db):
    cont = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=520)
    dd = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in (db.ordenes() or [])],
        width=520
    )
    def fila(p):
        txt = f"{p.get('cve_orden_parte')}# {p.get('part_no') or ''} ${p.get('precio',0)}\n{p.get('descripcion','')}"
        return ft.ListTile(title=ft.Text(txt))

    def actualizar(e=None):
        cont.controls.clear()
        if dd.value:
            for p in db.partes_orden(dd.value):
                cont.controls.append(fila(p))
        page.update()

    dd.on_change = actualizar
    dlg = ft.AlertDialog(
        title=ft.Text("Ver partes"),
        content=ft.Column([dd, ft.Container(cont, height=260, width=540)], tight=True, width=560),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nueva_parte_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    if not ordenes:
        page.open(ft.SnackBar(ft.Text("No hay órdenes para agregar partes.")))
        return
    dd_ord = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes],
        value=ordenes[0].cve_orden, width=540
    )
    dd_parte = ft.Dropdown(
        label="Pieza",
        options=[ft.dropdown.Option(text=f"{p['cve_parte']} {(p['part_no'] or '')} {p['descripcion']} ${p['precio']}",
                                    key=p["cve_parte"]) for p in db.partes()],
        width=540
    )
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd_ord.value or not dd_parte.value:
            err.value = "Seleccione todos los campos"; page.update(); return
        try:
            db.parte_orden(orden=dd_ord.value, parte=dd_parte.value)
            conn.commit()
            close()
            page.open(ft.SnackBar(ft.Text("Parte agregada con éxito")))
            open_partes_dialog(page, db)
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Añadir parte a orden"),
        content=ft.Column([dd_ord, dd_parte, err], tight=True, width=560),
        actions=[ft.ElevatedButton("Añadir", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()

# Aliases
open_parts_dialog = open_partes_dialog
open_new_part_dialog = open_nueva_parte_dialog