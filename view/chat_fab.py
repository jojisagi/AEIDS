# view/chat_fab.py
import os
import flet as ft

# Compatibilidad con versiones de Flet que exponen Colors/Icons con mayúscula
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

# Tus clases del chatbot (ajusta si tu módulo se llama distinto)
try:
    from chatbot_core import ControladorChatbot, Modelo4oMini, Modelo4o
except Exception:
    # Si no existe Modelo4o, trabajamos sólo con 4o-mini
    from chatbot_core import ControladorChatbot, Modelo4oMini
    class Modelo4o:  # stub para evitar crashear el cambio de modelo
        pass

def _get_api_key(page: ft.Page) -> str | None:
    # 1) almacenada localmente por la UI
    k = None
    try:
        k = page.client_storage.get("openai_api_key")
    except Exception:
        pass
    # 2) variable de entorno como fallback
    return k or os.getenv("OPENAI_API_KEY")

def make_chat_fab(page: ft.Page) -> ft.FloatingActionButton:
    """
    Devuelve un FloatingActionButton que abre un chat con el asistente.
    Se desactiva si no hay API key configurada.
    """
    api_key = _get_api_key(page)
    if not api_key:
        return ft.FloatingActionButton(
            icon=ft.icons.SMART_TOY_OUTLINED,
            text="Asistente",
            disabled=True,
            tooltip="Configura tu OpenAI API Key en 'Configurar conexiones'.",
        )

    # Construimos el controlador del chatbot, tolerando firmas distintas
    try:
        ctrl = ControladorChatbot(
            estrategia=Modelo4oMini(),
            contexto_inicial="Eres el asistente del sistema de órdenes. Responde breve y útil.",
            api_key=api_key,
        )
    except TypeError:
        # Firma alternativa sin api_key nombrado
        ctrl = ControladorChatbot(
            Modelo4oMini(),
            contexto_inicial="Eres el asistente del sistema de órdenes. Responde breve y útil.",
        )
        try:
            setattr(ctrl, "api_key", api_key)
        except Exception:
            pass

    # UI del chat
    chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=10)
    input_field = ft.TextField(
        hint_text="Escribe tu mensaje…",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=5,
    )

    # Dropdown para cambiar modelo en caliente (si tu controlador lo soporta)
    model_dd = ft.Dropdown(
        width=150,
        value="4o-mini",
        options=[ft.dropdown.Option("4o-mini"), ft.dropdown.Option("4o")],
    )

    def on_model_change(e=None):
        try:
            if model_dd.value == "4o":
                ctrl.cambiarmodelo(Modelo4o())
            else:
                ctrl.cambiarmodelo(Modelo4oMini())
        except Exception:
            # Si tu implementación no soporta cambiarmodelo, simplemente ignoramos
            pass

    model_dd.on_change = on_model_change

    def bubble(text: str, mine: bool) -> ft.Row:
        bg = ft.colors.BLUE_GREY_800 if mine else ft.colors.GREY_800
        align = ft.MainAxisAlignment.END if mine else ft.MainAxisAlignment.START
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(text, selectable=True, size=14),
                    bgcolor=bg,
                    padding=10,
                    border_radius=12,
                    width=440,
                )
            ],
            alignment=align,
        )

    def send_click(e=None):
        msg = (input_field.value or "").strip()
        if not msg:
            return
        input_field.value = ""
        chat_list.controls.append(bubble(msg, True))
        chat_list.controls.append(bubble("…", False))
        page.update()

        # Llamamos al modelo (tratamos ambas APIs: preguntar / enviarmensaje)
        try:
            if hasattr(ctrl, "preguntar"):
                resp = ctrl.preguntar(msg)
            else:
                turno = ctrl.enviarmensaje(msg)
                if isinstance(turno, list) and turno:
                    resp = turno[-1].get("content", "")
                else:
                    resp = str(turno)
        except Exception as ex:
            resp = f"Error: {ex}"

        # reemplazamos el "…" por la respuesta real
        chat_list.controls[-1] = bubble(resp, False)
        page.update()

    send_btn = ft.IconButton(icon=ft.icons.SEND, on_click=send_click)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.icons.SMART_TOY_OUTLINED), ft.Text("Asistente")], spacing=8),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Text("Modelo:"), model_dd],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    chat_list,
                    ft.Row([input_field, send_btn]),
                ],
                expand=True,
                tight=True,
                spacing=10,
            ),
            width=520,
            height=440,
            padding=16,
        ),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close_chat())],
        open=False,
    )

    def open_chat(e=None):
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def close_chat(e=None):
        dlg.open = False
        page.update()

    return ft.FloatingActionButton(
        icon=ft.icons.SMART_TOY_OUTLINED,
        text="Asistente",
        on_click=open_chat,
        tooltip="Abrir asistente",
    )

# Alias por compatibilidad con nombres antiguos
make_login_chatbot_fab = make_chat_fab