# view/reporte.py
import flet as ft
from decimal import Decimal

# Compat Colors (algunos entornos exponen Colors en vez de colors)
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors


# -------------------- Helpers numéricos --------------------
def _D(x) -> Decimal:
    """Convierte cualquier valor a Decimal de forma segura."""
    try:
        if x is None:
            return Decimal(0)
        if isinstance(x, (int, float, Decimal)):
            return Decimal(str(x))
        s = str(x).strip()
        # limpia formato común de dinero: $ 1,234.56
        s = s.replace("$", "").replace(",", "")
        return Decimal(s) if s else Decimal(0)
    except Exception:
        return Decimal(0)


def _fmt_money(x) -> str:
    """Formatea Decimal a string de dinero."""
    v = _D(x)
    return f"${v:,.2f}"


def open_reporte_dialog(page: ft.Page, db):
    # Carga inicial de órdenes
    ordenes = db.ordenes() or []
    dd = ft.Dropdown(
        label="Seleccione la orden",
        options=[
            ft.dropdown.Option(
                text=f"{o.cve_orden} {o.eq_modelo} {o.cliente}",
                key=str(o.cve_orden),
            )
            for o in ordenes
        ],
        width=540,
    )
    body = ft.Column(expand=True, alignment=ft.MainAxisAlignment.SPACE_AROUND)

    def _tarifa_y_nombre_tipo(cve_tipo):
        """
        Obtiene (tarifa_hora, nombre_tipo) desde db.tipos() tolerando formatos:
        - {id: "nombre"}
        - {id: {"nombre": "...", "tarifa_h": 250}} (o claves similares)
        - {id: [tarifa, nombre]} o (tarifa, nombre)
        - {id: {"descripcion": "...", "tarifa": "250"}}
        """
        tipos = db.tipos() or {}
        t = tipos.get(cve_tipo)

        tarifa = Decimal(0)
        nombre = str(cve_tipo)

        if isinstance(t, (list, tuple)):
            # Busca un número como tarifa y un string como nombre
            num = next(
                (
                    it for it in t
                    if isinstance(it, (int, float, Decimal))
                    or str(it).replace("$", "").replace(",", "").replace(".", "", 1).isdigit()
                ),
                None
            )
            txt = next((it for it in t if isinstance(it, str)), None)
            tarifa = _D(num)
            nombre = txt if txt is not None else str(t[-1])
        elif isinstance(t, dict):
            # nombres posibles
            for k in ("nombre", "descripcion", "tipo"):
                if k in t and t[k]:
                    nombre = str(t[k]).strip()
                    break
            # tarifas posibles
            for k in ("tarifa_h", "tarifa", "tarifa_hora"):
                if k in t and t[k] is not None:
                    tarifa = _D(t[k])
                    break
        elif isinstance(t, str):
            nombre = t
        elif t is not None:
            nombre = str(t)

        return tarifa, nombre

    def crear(ord_id):
        if not ord_id:
            return

        actual = next((o for o in db.ordenes() if str(o.cve_orden) == str(ord_id)), None)
        if not actual:
            return

        # Tarifa y nombre del tipo (se usa para el cálculo, no se muestra)
        tarifa, _tipo_txt = _tarifa_y_nombre_tipo(actual.cve_tipo_equipo)

        # Partes y servicios (precios robustos)
        piezas = db.partes_orden(actual.cve_orden) or []
        servicios = db.servicios_orden(actual.cve_orden) or []

        def _precio_from(d: dict) -> Decimal:
            if not isinstance(d, dict):
                return Decimal(0)
            for k in ("precio", "PRECIO", "costo", "monto", "importe"):
                if k in d and d[k] is not None:
                    return _D(d[k])
            return Decimal(0)

        total_piezas = sum((_precio_from(p) for p in piezas), Decimal(0))
        total_serv = sum((_precio_from(s) for s in servicios), Decimal(0))

        # Horas (suma de horas de técnicos de la orden)
        tecs = db.tecnicos_orden(actual.cve_orden, horas=True) or []
        horas = sum((_D(t.get("horas")) for t in tecs if isinstance(t, dict)), Decimal(0))

        total = total_piezas + total_serv + (tarifa * horas)

        # Render
        body.controls.clear()
        body.controls.append(
            ft.Column(
                [
                    ft.Text(f"Total de la orden: {_fmt_money(total)}", size=22, weight=ft.FontWeight.BOLD),
                    # Solo mostramos horas (se quitó la línea de Tarifa ...)
                    ft.Row(
                        [ft.Text(f"Horas: {horas}")],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Text(f"Total de piezas: {_fmt_money(total_piezas)}", size=22),
                    ft.Text(f"   Cant. de piezas: {len(piezas)}", size=16),
                    ft.Text(f"Total de servicios: {_fmt_money(total_serv)}", size=22),
                    ft.Text(f"   Cant. de servicios: {len(servicios)}", size=16),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            )
        )
        page.update()

    # Asegura que pase un entero (o al menos algo comparable) a crear()
    dd.on_change = lambda e: crear(dd.value)

    def close():
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Reporte por orden"),
        content=ft.Column([dd, body], tight=True, width=560, height=320),
        actions=[ft.TextButton("Salir", on_click=lambda e: close())],
        open=True,
    )

    page.overlay.append(dlg)
    page.update()


# Alias
open_report_dialog = open_reporte_dialog