# view/notas.py
import flet as ft

def open_notas_dialog(page: ft.Page, db):
    dd = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in db.ordenes()])
    lista = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

    def actualizar(e=None):
        lista.controls.clear()
        if dd.value:
            for n in (db.notas(int(dd.value)) or []):
                txt = n["nota"] if isinstance(n, dict) else str(n[0])
                lista.controls.append(ft.ListTile(title=ft.Text(txt)))
        page.update()
    dd.on_change = actualizar

    dlg = ft.AlertDialog(
        title=ft.Text("Notas por orden"),
        content=ft.Column([dd, ft.Container(lista, height=260, width=540)], tight=True, width=560),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update(); actualizar()

def open_nueva_nota_dialog(page: ft.Page, db, conn):
    ordenes = db.ordenes() or []
    dd = ft.Dropdown(label="Orden", options=[ft.dropdown.Option(text=f"{o.cve_orden} {o.eq_modelo}", key=o.cve_orden) for o in ordenes])
    nota = ft.TextField(label="Nota", multiline=True, min_lines=4, expand=True)
    err = ft.Text("", color="red")

    def guardar(e=None):
        if not dd.value or not (nota.value or "").strip():
            err.value = "Rellene todos los campos"; page.update(); return
        try:
            db.insertar_nota(int(dd.value), nota.value.strip())
            conn.commit()
            close()
            page.open(ft.SnackBar(ft.Text("Nota agregada con éxito")))
        except Exception as ex:
            err.value = f"Error: {ex}"; page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Nueva nota"),
        content=ft.Column([dd, nota, err], tight=True, width=560),
        actions=[ft.ElevatedButton("Agregar", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close())],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()