from __future__ import annotations
import os
import flet as ft

from chatbot_core import (
    ControladorChatbot,
    Modelo4oMini,
    Modelo4o,
    ChatMetrics,
)


# Solo para que el import `from .chat_fab import ChatbotFAB` no truene.
# Ya NO se usa directamente en la app, usamos `make_chat_fab(page)`.
class ChatbotFAB:
    pass


def make_chat_fab(page: ft.Page) -> ft.Control:
    """
    Crea el FAB del asistente y el panel de chat.
    Devuelve un Stack con:
      - overlay del chat (Container)
      - FloatingActionButton
    """

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    ctrl: ControladorChatbot | None = None

    # Column donde van las burbujas
    messages_column = ft.Column(
        auto_scroll=True,
        expand=True,
        spacing=6,
    )

    # Input del usuario
    input_field = ft.TextField(
        hint_text="Escribe tu mensaje...",
        expand=True,
        multiline=False,
    )

    # Dropdown de modelo
    model_dropdown = ft.Dropdown(
        label="Modelo:",
        options=[
            ft.dropdown.Option(key="4o", text="4o"),
            ft.dropdown.Option(key="4o-mini", text="4o-mini"),
        ],
        value="4o-mini",
        width=140,
    )

    # --------- helpers internos --------- #

    def estrategia_actual():
        if model_dropdown.value == "4o":
            return Modelo4o()
        return Modelo4oMini()

    def add_system_message(text: str):
        messages_column.controls.append(
            ft.Container(
                content=ft.Text(
                    text,
                    size=11,
                    italic=True,
                    color=ft.colors.GREY,
                ),
                alignment=ft.alignment.center,
                padding=4,
            )
        )
        page.update()

    def add_user_message(text: str):
        messages_column.controls.append(
            ft.Container(
                content=ft.Text(text),
                alignment=ft.alignment.center_right,
                padding=8,
                border_radius=16,
                bgcolor=ft.colors.BLUE_GREY_800,
            )
        )
        page.update()

    def add_bot_message(text: str, metrics: ChatMetrics | None = None):
        # Pegamos métricas en la MISMA burbuja para que se vea sí o sí
        full_text = text
        if metrics is not None:
            full_text += (
                "\n\n"
                f"[Modelo: {metrics.modelo} | "
                f"Prompt: {metrics.prompt_tokens} | "
                f"Respuesta: {metrics.completion_tokens} | "
                f"Total: {metrics.total_tokens} tokens | "
                f"{metrics.latency_ms:.0f} ms]"
            )

        print("=== METRICAS CHATBOT ===", full_text)  # debug consola

        messages_column.controls.append(
            ft.Container(
                content=ft.Text(
                    full_text,
                    size=12,
                    color=ft.colors.BLUE_GREY_50,
                ),
                alignment=ft.alignment.center_left,
                padding=8,
                border_radius=16,
                bgcolor=ft.colors.BLUE_GREY_700,
            )
        )
        page.update()

    # --------- inicializar controlador --------- #

    if api_key:
        try:
            ctrl = ControladorChatbot(
                estrategia=Modelo4oMini(),
                contexto_inicial=(
                    "Eres un asistente integrado al sistema de gestión de órdenes. "
                    "Responde de forma clara, breve y en español neutro."
                ),
                api_key=api_key,
            )
        except Exception as e:
            add_system_message(f"No se pudo inicializar el asistente: {e}")
            ctrl = None
    else:
        add_system_message(
            "Asistente deshabilitado: configura la variable de entorno OPENAI_API_KEY."
        )

    # --------- callbacks --------- #

    def on_model_change(e: ft.ControlEvent):
        nonlocal ctrl
        if ctrl:
            ctrl.cambiarmodelo(estrategia_actual())

    model_dropdown.on_change = on_model_change

    def send_message(_=None):
        nonlocal ctrl
        text = (input_field.value or "").strip()
        if not text:
            return

        add_user_message(text)
        input_field.value = ""
        page.update()

        if not ctrl:
            add_system_message("Chatbot no disponible (sin configuración).")
            return

        ctrl.cambiarmodelo(estrategia_actual())

        try:
            respuesta, metrics = ctrl.ask(text)
        except Exception as e:
            respuesta = f"[Error al llamar al asistente: {e}]"
            metrics = None

        add_bot_message(respuesta, metrics)

    input_field.on_submit = send_message

    # se rellena después de declararla para poder cerrar
    chat_overlay: ft.Container

    def toggle_visibility(_=None):
        chat_overlay.visible = not chat_overlay.visible
        page.update()

    # --------- layout panel de chat (misma vista que tenías) --------- #

    header = ft.Row(
        controls=[
            ft.Icon(ft.icons.WORKSPACES_OUTLINED, size=22),
            ft.Text("Asistente", weight=ft.FontWeight.BOLD, size=18),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.icons.CLOSE,
                on_click=toggle_visibility,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    chat_panel = ft.Container(
        bgcolor=ft.colors.BLUE_GREY_900,
        width=460,
        padding=20,
        border_radius=24,
        content=ft.Column(
            expand=True,
            spacing=12,
            controls=[
                header,
                ft.Row(
                    controls=[ft.Text("Modelo:"), model_dropdown],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(),
                ft.Container(expand=True, content=messages_column),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        input_field,
                        ft.IconButton(icon=ft.icons.SEND, on_click=send_message),
                    ],
                ),
                ft.TextButton("Cerrar", on_click=toggle_visibility),
            ],
        ),
    )

    chat_overlay = ft.Container(
        right=16,
        bottom=80,
        visible=False,
        content=chat_panel,
    )

    fab = ft.FloatingActionButton(
        icon=ft.icons.WORKSPACES_OUTLINED,
        text="Asistente",
        on_click=toggle_visibility,
    )

    stack = ft.Stack(
        controls=[
            chat_overlay,
            ft.Container(right=16, bottom=16, content=fab),
        ]
    )

    return stack