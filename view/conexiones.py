# view/conexiones.py
import os
import flet as ft
from utils.config import cargar_datos_conexion, guardar_datos_conexion
from .chat_fab import make_chat_fab

if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors

def _get_api_key(page: ft.Page):
    try:
        k = page.client_storage.get("openai_api_key")
    except Exception:
        k = None
    return k or os.getenv("OPENAI_API_KEY")

def open_conexiones_dialog(page: ft.Page):
    datos = cargar_datos_conexion("conexion_db.txt")

    oracle_port    = ft.TextField(label="Puerto",            width=300, value=datos["port"],         border_color=ft.colors.BLUE_300)
    oracle_host    = ft.TextField(label="Nombre Host",       width=300, value=datos["hostname"],     border_color=ft.colors.BLUE_300)
    oracle_service = ft.TextField(label="Nombre del Servicio", width=300, value=datos["service_name"], border_color=ft.colors.BLUE_300)
    mongo_conn     = ft.TextField(label="Cadena de Conexión", width=300, multiline=True, max_lines=7,
                                  value=datos["mongodb_url"], border_color=ft.colors.BLUE_300)
    openai_api_key_tf = ft.TextField(
        label="OpenAI API Key", password=True, can_reveal_password=True, width=300,
        border_color=ft.colors.BLUE_300, value=_get_api_key(page) or ""
    )
    msg = ft.Text("", text_align=ft.TextAlign.CENTER)

    def guardar(e=None):
        ok_conn = all([
            (oracle_host.value or "").strip(),
            (oracle_port.value or "").strip(),
            (oracle_service.value or "").strip(),
            (mongo_conn.value or "").strip(),
        ])
        if ok_conn:
            guardar_datos_conexion(
                "conexion_db.txt",
                hostname=oracle_host.value.strip(),
                port=oracle_port.value.strip(),
                service_name=oracle_service.value.strip(),
                mongodb_url=mongo_conn.value.strip(),
            )

        api = (openai_api_key_tf.value or "").strip()
        try:
            if api: page.client_storage.set("openai_api_key", api)
            else:   page.client_storage.remove("openai_api_key")
        except Exception:
            pass

        msg.value = "Información guardada" if ok_conn else "Configure todas las conexiones"
        msg.color = "green" if ok_conn else "red"

        # refresca el FAB (se desactiva/activa según API key)
        page.floating_action_button = make_chat_fab(page)
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Configuración de Conexiones"),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Servidor Oracle SQL", size=20, weight=ft.FontWeight.BOLD),
                    oracle_port, oracle_host, oracle_service,
                    ft.Divider(height=10, thickness=1),
                    ft.Text("Servidor MongoDB", size=20, weight=ft.FontWeight.BOLD),
                    mongo_conn,
                    ft.Divider(height=10, thickness=1),
                    ft.Text("OpenAI", size=20, weight=ft.FontWeight.BOLD),
                    openai_api_key_tf,
                    msg,
                ]
            ),
        ),
        actions=[ft.ElevatedButton("Guardar", on_click=guardar),
                 ft.ElevatedButton("Salir", on_click=lambda e: close(), color=ft.colors.RED)],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()

def open_acerca_de_dialog(page: ft.Page):
    texto = (
        "Proyecto final \nDiseño y Programación de Bases de datos\nVersión: 1\n"
        "Integrantes: Candelario Sandoval Isai, González Espinosa Héctor Armando\n"
        "Jaimes Calderón Cesar Daniel, Leyva Durante Adrián Emiliano\n"
        "Soto Natera Sebastián \n\n"
        "Versión 2.0\nAnálisis y Diseño de Sistemas\nIntegrantes:\n"
        "Cerdeira Bengoechea Axel\nGonzález Espinosa Héctor Armando\n"
        "Ruiz Cerdeño Patricio\nSánchez Girón Jorge\n\n"
        "Versión 3.0\nArquitectura e Ingeniería de Software\nIntegrantes:\n"
        "Cerdeira Bengoechea Axel\nGonzález Espinosa Héctor Armando\n"
        "Ruiz Cerdeño Patricio\nSánchez Girón Jorge"
    )
    dlg = ft.AlertDialog(
        title=ft.Text("Acerca de"),
        content=ft.Text(texto),
        actions=[ft.ElevatedButton("Cerrar", on_click=lambda e: close(), color=ft.colors.RED)],
        open=True,
    )
    def close(): dlg.open=False; page.update()
    page.overlay.append(dlg); page.update()