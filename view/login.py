# login.py
import os
import flet as ft
from utils.config import cargar_datos_conexion, guardar_datos_conexion
from controller.app_controller import AppController
from model.usuario import usuarios_default
from dashboard import build_dashboard_view   # <- sin círculos; dashboard NO importa login

VALID_USER = "cib700_01"
VALID_PASS = "Hector701%/01."

def _get_api_key(page: ft.Page) -> str | None:
    return page.client_storage.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

def _open_conexiones_dialog(page: ft.Page):
    datos = cargar_datos_conexion("conexion_db.txt")

    host  = ft.TextField(label="Host",     width=300, value=datos["hostname"])
    port  = ft.TextField(label="Puerto",   width=300, value=datos["port"])
    svc   = ft.TextField(label="Servicio", width=300, value=datos["service_name"])
    mongo = ft.TextField(label="MongoDB",  width=300, multiline=True, value=datos["mongodb_url"])
    api   = ft.TextField(label="OpenAI API Key", width=300, password=True,
                         can_reveal_password=True, value=_get_api_key(page) or "")
    msg   = ft.Text("", size=12)

    def guardar(e=None):
        ok = all((host.value or "").strip(),
                 (port.value or "").strip(),
                 (svc.value or "").strip(),
                 (mongo.value or "").strip())
        if ok:
            guardar_datos_conexion("conexion_db.txt",
                                   hostname=host.value.strip(),
                                   port=port.value.strip(),
                                   service_name=svc.value.strip(),
                                   mongodb_url=mongo.value.strip())
        # API key local
        key = (api.value or "").strip()
        if key:
            page.client_storage.set("openai_api_key", key)
        else:
            try: page.client_storage.remove("openai_api_key")
            except Exception: pass

        msg.value = "Información guardada" if ok else "Faltan campos"
        msg.color = "green" if ok else "red"
        page.update()

    def cerrar(e=None):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Configuración de Conexiones"),
        content=ft.Column([host, port, svc, mongo, api, msg], tight=True, width=360),
        actions=[ft.ElevatedButton("Guardar", on_click=guardar),
                 ft.TextButton("Salir", on_click=cerrar)],
        open=True
    )
    page.overlay.append(dlg)
    page.update()

def build_login_view(page: ft.Page) -> ft.View:
    page.title = "Inicio de Sesión"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    datos = cargar_datos_conexion("conexion_db.txt")

    user_tf = ft.TextField(label="Usuario", width=300, border_color=ft.colors.BLUE_300)
    pass_tf = ft.TextField(label="Contraseña", width=300, password=True, can_reveal_password=True,
                           border_color=ft.colors.BLUE_300)

    msg = ft.Text("", color="red", text_align=ft.TextAlign.CENTER)
    spinner = ft.ProgressRing(visible=False)

    def do_login(e=None):
        msg.value = ""
        spinner.visible = True
        login_btn.disabled = True
        page.update()

        username = (user_tf.value or "").strip()
        password = (pass_tf.value or "").strip()

        if username != VALID_USER or password != VALID_PASS:
            msg.value = "Usuario o contraseña incorrectos."
            spinner.visible = False
            login_btn.disabled = False
            page.update()
            return

        # Conexión a BD usando datos guardados
        try:
            ctrl = AppController()
            db, conn = ctrl.connect(
                datos["hostname"], datos["port"], datos["service_name"],
                username=username, password=password
            )
        except Exception as ex:
            db, conn = None, None

        if conn is None:
            msg.value = "No se pudo establecer conexión con la base de datos."
            spinner.visible = False
            login_btn.disabled = False
            page.update()
            return

        user_tf.value = pass_tf.value = ""
        usuarios = usuarios_default() or []
        user = next((u for u in usuarios if u.name == username), None) or usuarios[0]

        # Empujar el dashboard
        page.views.append(build_dashboard_view(page, db, conn, user))
        page.go("/dashboard")

        # Limpia estado visual
        spinner.visible = False
        login_btn.disabled = False
        msg.value = ""
        page.update()

    login_btn = ft.ElevatedButton("Iniciar sesión", on_click=do_login)
    conexiones_btn = ft.TextButton("Configurar conexiones", on_click=lambda e: _open_conexiones_dialog(page))

    return ft.View(
        route="/",
        controls=[
            ft.Row([ft.Container(), conexiones_btn], alignment=ft.MainAxisAlignment.END),
            ft.Column(
                [
                    ft.Text("Iniciar Sesión", size=28, weight=ft.FontWeight.BOLD),
                    user_tf,
                    pass_tf,
                    login_btn,
                    msg,
                    spinner,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )