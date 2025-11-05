# view/dashboard.py
import flet as ft
from view.chat_fab import attach_dashboard_chatbot
from view.notas import open_notas_dialog, open_nueva_nota_dialog
from view.partes import open_partes_dialog, open_nueva_parte_dialog
from view.servicios import open_servicios_dialog, open_nuevo_servicio_dialog
from view.reporte import open_reporte_dialog

def view_dashboard(page: ft.Page, state) -> ft.View:
    page.title = "Página principal"

    if not state.conn:  # si alguien llegó sin login
        page.go("/login")

    # Top bar
    info = ft.Row(
        [ft.Text(f"Usuario: {getattr(state.user,'name','?')}"), ft.Container(), ft.ElevatedButton("Cerrar sesión", on_click=lambda e: logout())],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    # Widgets principales (simplificados)
    btn_reporte = ft.ElevatedButton("Obtener Reporte", on_click=lambda e: open_reporte_dialog(page, state.db))
    btn_nueva   = ft.ElevatedButton("Nueva Orden", on_click=lambda e: page.open(ft.SnackBar(ft.Text("TODO: ir a view nueva orden"))))
    btn_partes  = ft.ElevatedButton("Ver Partes", on_click=lambda e: open_partes_dialog(page, state.db))
    btn_add_par = ft.ElevatedButton("Añadir Parte", on_click=lambda e: open_nueva_parte_dialog(page, state.db, state.conn))
    btn_servs   = ft.ElevatedButton("Ver Servicios", on_click=lambda e: open_servicios_dialog(page, state.db))
    btn_add_ser = ft.ElevatedButton("Añadir Servicio", on_click=lambda e: open_nuevo_servicio_dialog(page, state.db, state.conn))
    btn_notas   = ft.ElevatedButton("Ver Notas", on_click=lambda e: open_notas_dialog(page, state.db))
    btn_add_not = ft.ElevatedButton("Nueva Nota", on_click=lambda e: open_nueva_nota_dialog(page, state.db, state.conn))

    # Tabla rápida de órdenes
    table = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    def refresh():
        table.controls.clear()
        try:
            ordenes = state.db.ordenes()
        except Exception as ex:
            table.controls.append(ft.Text(f"Error cargando órdenes: {ex}", color="red"))
            page.update(); return
        header = ft.Row([
            ft.Text("Clave", width=70, weight=ft.FontWeight.BOLD),
            ft.Text("Marca", width=150, weight=ft.FontWeight.BOLD),
            ft.Text("Modelo", width=150, weight=ft.FontWeight.BOLD),
            ft.Text("Status", width=120, weight=ft.FontWeight.BOLD),
        ])
        table.controls.append(header); table.controls.append(ft.Divider())
        for o in ordenes:
            table.controls.append(
                ft.Row([
                    ft.Text(str(o.cve_orden), width=70),
                    ft.Text(o.eq_marca, width=150),
                    ft.Text(o.eq_modelo, width=150),
                    ft.Text(str(o.cve_status), width=120),
                ])
            )
        page.update()
    refresh()

    def logout():
        try:
            if state.db: state.db.close_connection()
        except Exception: pass
        state.db = None; state.conn = None; state.user = None
        page.go("/login")

    # Asistente flotante del dashboard (inyecta db/conn)
    attach_dashboard_chatbot(page, state)

    return ft.View(
        route="/dashboard",
        controls=[
            info, ft.Divider(),
            ft.Row([btn_reporte, btn_nueva, btn_notas, btn_add_not, btn_partes, btn_add_par, btn_servs, btn_add_ser], wrap=True, spacing=12),
            ft.Divider(height=20, thickness=1),
            table
        ],
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )