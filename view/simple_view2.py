# view/simple_view2.py
import flet as ft
from .login import build_login_view
from .chat_fab import make_chat_fab  # FAB (se desactiva si no hay API key)
from .chat_fab import ChatbotFAB

def main(page: ft.Page):
    page.title = "App Órdenes — Módulos"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # back stack
    def on_view_pop(e):
        page.views.pop()
        page.go(page.views[-1].route if page.views else "/")
    page.on_view_pop = on_view_pop

    page.views.clear()
    page.views.append(build_login_view(page))
    page.floating_action_button = make_chat_fab(page)  # activo/inhabilitado según API key
    page.go("/")
    page.update()

if __name__ == "__main__":
    ft.app(target=main)