# view/login.py
import flet as ft
import os

# Compatibilidad Flet (Colors/Icons)
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

# ↓ Ajusta a tus rutas reales de módulos del proyecto
from utils.config import cargar_datos_conexion
from controller.app_controller import AppController
from model.usuario import usuarios_default

from .dashboard import build_dashboard_view
from .conexiones import open_conexiones_dialog, open_acerca_de_dialog
from .chat_fab import make_chat_fab

# Credenciales “demo” como en simple_view.py
VALID_USER = "cib700_01"
VALID_PASS = "Hector701%/01."

def build_login_view(page: ft.Page) -> ft.View:
    page.title = "Inicio de Sesión"

    # UI
    login_message = ft.Text("", color="red", text_align=ft.TextAlign.CENTER)
    user_tf = ft.TextField(label="Usuario", width=300, border_color=ft.colors.BLUE_300)
    pass_tf = ft.TextField(label="Contraseña", password=True, can_reveal_password=True,
                           width=300, border_color=ft.colors.BLUE_300)

    loading = ft.ProgressRing(visible=False)

    # Botones secundarios
    btn_cfg = ft.TextButton("Configurar conexiones", on_click=lambda e: open_conexiones_dialog(page))
    btn_about = ft.TextButton("Acerca de", on_click=lambda e: open_acerca_de_dialog(page))

    def do_login(e=None):
        login_message.value = ""
        loading.visible = True
        btn_login.disabled = True
        page.update()

        u = (user_tf.value or "").strip()
        p = (pass_tf.value or "").strip()

        if u != VALID_USER or p != VALID_PASS:
            login_message.value = "Usuario o contraseña incorrectos."
            loading.visible = False
            btn_login.disabled = False
            page.update()
            return

        # Datos de conexión a BD desde archivo
        datos = cargar_datos_conexion("conexion_db.txt")
        controller = AppController()
        try:
            db_instance, connection = controller.connect(
                datos["hostname"], datos["port"], datos["service_name"],
                username=u, password=p
            )
        except Exception:
            db_instance, connection = (None, None)

        if connection is None:
            login_message.value = "No se pudo establecer conexión con la base de datos."
            loading.visible = False
            btn_login.disabled = False
            page.update()
            return

        # Usuario app (como en simple_view.py)
        usuarios = usuarios_default() or []
        user = next((x for x in usuarios if x.name == u), None) or usuarios[0]

        # Limpia y navega
        user_tf.value = ""
        pass_tf.value = ""
        page.views.append(build_dashboard_view(page, db_instance, connection, user))
        page.go("/dashboard")
        page.title = "Página principal"
        loading.visible = False
        btn_login.disabled = False
        page.update()

    btn_login = ft.ElevatedButton("Iniciar Sesión", on_click=do_login)

    # Retorna la View
    return ft.View(
        "/",
        controls=[
            ft.Row([ft.Container(), btn_cfg], alignment=ft.MainAxisAlignment.END),
            ft.Column(
                [
                    ft.Text("Iniciar Sesión", size=30, weight=ft.FontWeight.BOLD),
                    user_tf, pass_tf, btn_login, login_message, loading,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row([ft.Container(), btn_about], alignment=ft.MainAxisAlignment.END),
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        floating_action_button=make_chat_fab(page),  # FAB también disponible aquí
    )