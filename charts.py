# view/charts.py
from __future__ import annotations
import flet as ft
from typing import Callable, Dict


def _count_statuses(db_instance, ui_status_name_fn: Callable[[int | str | None], str]) -> Dict[str, int]:
    """Cuenta órdenes por estatus (En proceso, Terminado, Recogido) usando el nombre UI normalizado."""
    try:
        ordenes = db_instance.ordenes() or []
    except Exception:
        ordenes = []

    counts = {"En proceso": 0, "Terminado": 0, "Recogido": 0}
    for o in ordenes:
        ui = ui_status_name_fn(getattr(o, "cve_status", None))
        if ui in counts:
            counts[ui] += 1
    return counts


def open_status_chart_dialog(page: ft.Page, db_instance, ui_status_name_fn: Callable[[int | str | None], str]) -> None:
    """Muestra un diálogo con una gráfica de barras por estatus de órdenes."""
    counts = _count_statuses(db_instance, ui_status_name_fn)

    # Intentamos crear la gráfica con la API moderna de Flet.
    # Si falla (versiones antiguas), mostramos un fallback de texto.
    try:
        chart = ft.BarChart(
            bar_groups=[
                ft.BarChartGroup(
                    x=0,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=float(counts["En proceso"]),
                            color=ft.colors.DEEP_PURPLE,
                            tooltip=f"En proceso: {counts['En proceso']}",
                        )
                    ],
                ),
                ft.BarChartGroup(
                    x=1,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=float(counts["Terminado"]),
                            color=ft.colors.GREEN,
                            tooltip=f"Terminado: {counts['Terminado']}",
                        )
                    ],
                ),
                ft.BarChartGroup(
                    x=2,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=float(counts["Recogido"]),
                            color=ft.colors.AMBER_900,
                            tooltip=f"Recogido: {counts['Recogido']}",
                        )
                    ],
                ),
            ],
            # Opcionales; si tu versión no los soporta, puedes comentarlos.
            # border=ft.border.all(1, ft.colors.GREY_300),
            # animate=200,
        )

        legend = ft.Row(
            [
                ft.Container(width=14, height=14, bgcolor=ft.colors.DEEP_PURPLE, border_radius=3),
                ft.Text("En proceso"),
                ft.Container(width=10),
                ft.Container(width=14, height=14, bgcolor=ft.colors.GREEN, border_radius=3),
                ft.Text("Terminado"),
                ft.Container(width=10),
                ft.Container(width=14, height=14, bgcolor=ft.colors.AMBER_900, border_radius=3),
                ft.Text("Recogido"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )

        content = ft.Container(
            width=580,
            content=ft.Column(
                [
                    ft.Text("Órdenes por estatus", size=18, weight=ft.FontWeight.BOLD),
                    chart,
                    legend,
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    except Exception as ex:
        # Fallback seguro si tu versión de Flet no soporta BarChart
        content = ft.Container(
            width=480,
            content=ft.Column(
                [
                    ft.Text("Órdenes por estatus", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"En proceso: {counts['En proceso']}"),
                    ft.Text(f"Terminado: {counts['Terminado']}"),
                    ft.Text(f"Recogido: {counts['Recogido']}"),
                    ft.Container(height=10),
                    ft.Text(
                        f"(Vista simplificada por compatibilidad: {ex})",
                        size=12,
                        italic=True,
                        color=ft.colors.GREY,
                    ),
                ],
                tight=True,
            ),
        )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Gráfica de estatus"),
        content=content,
        actions=[ft.ElevatedButton("Cerrar", on_click=lambda e: page.close(dlg))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    try:
        page.open(dlg)
    except Exception:
        page.dialog = dlg
        dlg.open = True
        page.update()