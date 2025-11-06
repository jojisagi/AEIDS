# view/charts.py
from __future__ import annotations
import flet as ft
from typing import Callable, Dict


def _count_statuses(db_instance, ui_status_name_fn: Callable[[int | str | None], str]) -> Dict[str, int]:
    """Cuenta órdenes por estatus usando el nombre UI normalizado."""
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


def _bottom_axis(labels: dict[str, str]) -> ft.ChartAxis:
    return ft.ChartAxis(
        labels=[
            ft.ChartAxisLabel(value=0, label=ft.Container(ft.Text(labels["En proceso"], size=12))),
            ft.ChartAxisLabel(value=1, label=ft.Container(ft.Text(labels["Terminado"], size=12))),
            ft.ChartAxisLabel(value=2, label=ft.Container(ft.Text(labels["Recogido"], size=12))),
        ]
    )


def open_status_chart_dialog(page: ft.Page, db_instance, ui_status_name_fn: Callable[[int | str | None], str]) -> None:
    """Gráfica de barras por estatus sin tooltips (evita comillas escapadas)."""
    counts = _count_statuses(db_instance, ui_status_name_fn)

    labels_ui = {
        "En proceso": "En proceso",
        "Terminado": "Terminado",
        "Recogido": "Recogido" if counts["Recogido"] == 1 else "Recogidos",
    }

    max_y = max(counts.values()) if counts else 0
    max_y = (max_y + 1) if max_y > 0 else 1

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
                            tooltip=None,  # ← desactivado para evitar comillas
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
                            tooltip=None,  # ← desactivado
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
                            tooltip=None,  # ← desactivado
                        )
                    ],
                ),
            ],
            bottom_axis=_bottom_axis(labels_ui),
            max_y=max_y,
        )

        # Leyenda con conteos (reemplaza a los tooltips)
        legend = ft.Row(
            [
                ft.Container(width=14, height=14, bgcolor=ft.colors.DEEP_PURPLE, border_radius=3),
                ft.Text(f"{labels_ui['En proceso']}: {counts['En proceso']}"),
                ft.Container(width=16),
                ft.Container(width=14, height=14, bgcolor=ft.colors.GREEN, border_radius=3),
                ft.Text(f"{labels_ui['Terminado']}: {counts['Terminado']}"),
                ft.Container(width=16),
                ft.Container(width=14, height=14, bgcolor=ft.colors.AMBER_900, border_radius=3),
                ft.Text(f"{labels_ui['Recogido']}: {counts['Recogido']}"),
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
        # Fallback de texto
        content = ft.Container(
            width=480,
            content=ft.Column(
                [
                    ft.Text("Órdenes por estatus", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{labels_ui['En proceso']}: {counts['En proceso']}"),
                    ft.Text(f"{labels_ui['Terminado']}: {counts['Terminado']}"),
                    ft.Text(f"{labels_ui['Recogido']}: {counts['Recogido']}"),
                    ft.Container(height=10),
                    ft.Text(f"(Vista simplificada por compatibilidad: {ex})",
                           size=12, italic=True, color=ft.colors.GREY),
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