# view/notas.py
import flet as ft

if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors

def open_notas_dialog(page: ft.Page, db):
    ordenes = db.ordenes() or []
    dd = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes],
        width=540
    )
    lista = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

    def actualizar(e=None):
        lista.controls.clear()
        if dd.value:
            try:
                notas = db.notas(int(dd.value)) or []
            except Exception:
                notas = []
            for n in notas:
                txt = n.get("nota") if isinstance(n, dict) else str(n)
                lista.controls.append(ft.ListTile(title=ft.Text(txt or "(nota vacía)")))
        page.update()

    dd.on_change = actualizar
    dlg = ft.AlertDialog(
        title=ft.Text("Notas por orden"),
        content=ft.Column([dd, ft.Container(lista, height=260, width=540)], tight=True, width=560),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open = False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nueva_nota_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    if not ordenes:
        page.open(ft.SnackBar(ft.Text("No hay órdenes para asociar la nota.")))
        return
    dd = ft.Dropdown(
        label="Orden",
        options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes],
        width=540,
        value=ordenes[0].cve_orden,
    )
    campo = ft.TextField(label="Nota", multiline=True, min_lines=4, expand=True, border_color=ft.colors.BLUE_300)
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd.value or not (campo.value or "").strip():
            err.value = "Rellene todos los campos"; page.update(); return
        try:
            db.insertar_nota(int(dd.value), campo.value.strip())
            conn.commit()
            close()
            page.open(ft.SnackBar(ft.Text("Nota agregada con éxito")))
            open_notas_dialog(page, db)  # abre el visor
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Nueva nota"),
        content=ft.Column([dd, campo, err], tight=True, width=560),
        actions=[ft.ElevatedButton("Agregar", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()

# Aliases (por si importaste en inglés)
open_notes_dialog = open_notas_dialog
open_new_note_dialog = open_nueva_nota_dialog