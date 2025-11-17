from __future__ import annotations
import flet as ft

from chatbot_core import (
    ControladorChatbot,
    Modelo4oMini,
    Modelo4o,
    ChatMetrics,
)


class ChatbotFAB(ft.UserControl):
    """
    Ventana de asistente con:
    - Selector de modelo (4o / 4o-mini)
    - Chat
    - Línea de métricas debajo de cada respuesta del bot:
      modelo • tokens • latencia ms
    """

    def __init__(self, api_key: str | None = None):
        super().__init__()
        self.api_key = api_key
        self.ctrl: ControladorChatbot | None = None

        # Área donde se agregan las burbujas
        self.messages_column = ft.Column(
            auto_scroll=True,
            expand=True,
            spacing=6,
        )

        # Input del usuario
        self.input_field = ft.TextField(
            hint_text="Escribe tu mensaje...",
            expand=True,
            multiline=False,
            on_submit=self._on_send_submit,
        )

        # Dropdown de modelo
        self.model_dropdown = ft.Dropdown(
            label="Modelo:",
            options=[
                ft.dropdown.Option(key="4o", text="4o"),
                ft.dropdown.Option(key="4o-mini", text="4o-mini"),
            ],
            value="4o-mini",
            width=140,
            on_change=self._on_model_change,
        )

        self.chat_overlay: ft.Container | None = None

    # ------------------ Ciclo de vida ------------------ #

    def did_mount(self):
        # Inicializa el controlador con el modelo por defecto (4o-mini)
        try:
            self.ctrl = ControladorChatbot(
                estrategia=Modelo4oMini(),
                contexto_inicial=(
                    "Eres un asistente integrado al sistema de gestión de órdenes. "
                    "Responde de forma clara, breve y en español neutro."
                ),
                api_key=self.api_key,
            )
        except Exception as e:
            self._add_system_message(f"No se pudo inicializar el asistente: {e}")

    # ------------------ Helpers ------------------ #

    def _estrategia_actual(self):
        """Devuelve la estrategia según el valor del dropdown."""
        if self.model_dropdown.value == "4o":
            return Modelo4o()
        return Modelo4oMini()

    def _on_model_change(self, e: ft.ControlEvent):
        """Cuando cambias el modelo en el combo, actualiza la estrategia."""
        if self.ctrl:
            self.ctrl.cambiarmodelo(self._estrategia_actual())

    def _add_user_message(self, text: str):
        self.messages_column.controls.append(
            ft.Container(
                content=ft.Text(text),
                alignment=ft.alignment.center_right,
                padding=8,
                border_radius=16,
                bgcolor=ft.colors.BLUE_GREY_800,
            )
        )
        self.update()

    def _add_bot_message(self, text: str):
        """Burbujita del bot (solo texto de la respuesta)."""
        self.messages_column.controls.append(
            ft.Container(
                content=ft.Text(text),
                alignment=ft.alignment.center_left,
                padding=8,
                border_radius=16,
                bgcolor=ft.colors.BLUE_GREY_700,
            )
        )
        self.update()

    def _add_metrics_line(self, metrics: ChatMetrics | None):
        """
        Línea pequeña con las métricas del último turno, debajo de la burbuja del bot.
        Siempre muestra algo (aunque las métricas sean None) para debug.
        """
        if metrics is None:
            texto = "[DEBUG] Sin métricas (metrics=None)"
        else:
            texto = (
                f"{metrics.modelo} • "
                f"{metrics.total_tokens} tokens "
                f"(prompt {metrics.prompt_tokens}, "
                f"respuesta {metrics.completion_tokens}) • "
                f"{metrics.latency_ms:.0f} ms"
            )

        # DEBUG: también imprime en la consola
        print("=== METRICAS CHATBOT ===", texto)

        self.messages_column.controls.append(
            ft.Container(
                content=ft.Text(
                    texto,
                    size=10,
                    color=ft.colors.AMBER_200,  # bien visible
                ),
                padding=ft.padding.only(left=24, bottom=4, top=2),
                alignment=ft.alignment.center_left,
            )
        )
        self.update()

    def _add_system_message(self, text: str):
        self.messages_column.controls.append(
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
        self.update()

    # ------------------ Eventos ------------------ #

    def _on_send_submit(self, e: ft.ControlEvent):
        self._send_message()

    def _on_send_click(self, e: ft.ControlEvent):
        self._send_message()

    def _send_message(self):
        text = (self.input_field.value or "").strip()
        if not text:
            return

        # Burbujita del usuario
        self._add_user_message(text)
        self.input_field.value = ""
        self.update()

        if not self.ctrl:
            self._add_system_message("Chatbot no disponible (sin configuración).")
            return

        # Asegura que el modelo seleccionado esté activo
        self.ctrl.cambiarmodelo(self._estrategia_actual())

        try:
            # ask() ya ejecuta todos los aspectos (seguridad, latencia, tokens)
            respuesta, metrics = self.ctrl.ask(text)
        except Exception as e:
            respuesta = f"[Error al llamar al asistente: {e}]"
            metrics = None

        # Burbujita del bot
        self._add_bot_message(respuesta)
        # Línea de métricas debajo (siempre se dibuja)
        self._add_metrics_line(metrics)

    # ------------------ Layout ------------------ #

    def build(self):
        header = ft.Row(
            controls=[
                ft.Icon(ft.icons.WORKSPACES_OUTLINED, size=22),
                ft.Text("Asistente", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.CLOSE,
                    on_click=lambda e: self._toggle_visibility(False),
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
                        controls=[
                            ft.Text("Modelo:"),
                            self.model_dropdown,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Divider(),
                    ft.Container(
                        expand=True,
                        content=self.messages_column,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self.input_field,
                            ft.IconButton(
                                icon=ft.icons.SEND,
                                on_click=self._on_send_click,
                            ),
                        ],
                    ),
                    ft.TextButton(
                        "Cerrar",
                        on_click=lambda e: self._toggle_visibility(False),
                    ),
                ],
            ),
        )

        self.chat_overlay = ft.Container(
            right=16,
            bottom=80,
            visible=False,
            content=chat_panel,
        )

        fab = ft.FloatingActionButton(
            icon=ft.icons.WORKSPACES_OUTLINED,
            text="Asistente",
            on_click=lambda e: self._toggle_visibility(),
        )

        return ft.Stack(
            controls=[
                self.chat_overlay,
                ft.Container(
                    right=16,
                    bottom=16,
                    content=fab,
                ),
            ],
        )

    def _toggle_visibility(self, force: bool | None = None):
        if self.chat_overlay is None:
            return

        if force is None:
            self.chat_overlay.visible = not self.chat_overlay.visible
        else:
            self.chat_overlay.visible = force

        self.update()