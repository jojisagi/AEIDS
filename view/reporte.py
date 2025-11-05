# app/views/reporte.py
import flet as ft
from routes import R

def view(page: ft.Page, db_instance, conn):
    def resumir(o): return f"{o.cve_orden} {o.eq_modelo} {o.cliente}"

    ordenes_dd = ft.Dropdown(options=[], label="Seleccione la orden", width=540)
    reporte    = ft.Column(expand=True)
    error      = ft.Text("", color=ft.colors.RED)

    def _tarifa_y_nombre_tipo(cve_tipo):
        tipos = db_instance.tipos() or {}
        try:
            tarifa, nombre = tipos[cve_tipo][0], tipos[cve_tipo][1]
        except Exception:
            t = tipos.get(cve_tipo)
            if isinstance(t, dict):
                tarifa = t.get("tarifa", 0)
                nombre = t.get("descripcion", str(cve_tipo))
            else:
                tarifa = 0; nombre = str(t or cve_tipo)
        return tarifa, nombre

    def crear_reporte(ord_id):
        if not ord_id: return
        actual = next((o for o in db_instance.ordenes() if str(o.cve_orden) == str(ord_id)), None)
        if not actual: return

        tarifa, tipo_txt = _tarifa_y_nombre_tipo(actual.cve_tipo_equipo)
        piezas    = db_instance.partes_orden(actual.cve_orden) or []
        servicios = db_instance.servicios_orden(actual.cve_orden) or []

        total_piezas = sum(p.get("precio", 0) for p in piezas if isinstance(p, dict))
        total_serv   = sum(s.get("precio", 0) for s in servicios if isinstance(s, dict))
        horas        = int(actual.horas or 0)
        total        = total_piezas + total_serv + (tarifa * horas)

        reporte.controls = [
            ft.Text(f"Total de la orden: ${total}", size=22, weight=ft.FontWeight.BOLD),
            ft.Row([ft.Text(f"\tTarifa {tipo_txt}:"), ft.Text(f" ${tarifa}"),
                    ft.Text("Horas:", expand=True, text_align=ft.TextAlign.END), ft.Text(f" {horas}")]),
            ft.Text(f"Total de piezas: ${total_piezas}", size=18),
            ft.Text(f"Total de servicios: ${total_serv}", size=18),
        ]
        page.update()

    def cargar_ordenes():
        try:
            os = db_instance.ordenes()
        except Exception as ex:
            error.value = f"Error cargando órdenes: {ex}"
            page.update(); return
        ordenes_dd.options = [ft.dropdown.Option(text=resumir(o), key=o.cve_orden) for o in os]
        page.update()

    ordenes_dd.on_change = lambda e: crear_reporte(ordenes_dd.value)
    cargar_ordenes()

    return ft.View(
        R.ORD_REPORTE,
        controls=[
            ft.Row([ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda e: page.go(R.DASH)),
                    ft.Text("Reporte por orden", size=22, weight=ft.FontWeight.BOLD)]),
            error, ordenes_dd, reporte
        ],
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )