# view/chat_fab.py
import flet as ft
from chatbot_core import ControladorChatbot, Modelo4oMini

def _get_api_key(page: ft.Page) -> str | None:
    import os
    return page.client_storage.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

def make_login_chatbot_fab(page: ft.Page, user_tf, pass_tf,
                           oracle_host, oracle_port, oracle_service, mongo_connection,
                           state):
    """
    FAB para la pantalla de login. Permite /probar -> conecta con los valores guardados en state.datos + usuario/pass.
    """
    ctrl = ControladorChatbot(
        estrategia=Modelo4oMini(),
        contexto_inicial=("Eres un asistente para probar la conexión Oracle. Comando /probar valida SELECT 1 FROM dual."),
        api_key=_get_api_key(page)
    )

    chat = _build_dialog(page)
    lv, inp = chat["lv"], chat["inp"]

    def probar():
        try:
            d = state.datos
            host, port, svc = d["hostname"], d["port"], d["service_name"]
            usr, pwd = (user_tf.value or "").strip(), (pass_tf.value or "")
            if not all([host, port, svc, usr, pwd]):
                return "Completa host/puerto/servicio/usuario/contraseña."
            c = state.controller or None
            if c is None:
                from controller.app_controller import AppController
                c = AppController()
            db, conn = c.connect(host, port, svc, usr, pwd)
            if conn is None:
                return "No se pudo conectar."
            cur = conn.cursor(); cur.execute("SELECT 1 FROM dual"); cur.fetchone()
            try: db.close_connection()
            except Exception: pass
            return "✅ Conexión OK."
        except Exception as ex:
            return f"❌ Error: {ex}"

    def send(_=None):
        msg = (inp.value or "").strip()
        if not msg: return
        inp.value = ""
        lv.controls.append(_bubble(msg, True))
        if msg.lower().startswith("/probar"):
            ans = probar()
        else:
            try: ans = ctrl.preguntar(msg)
            except Exception as ex: ans = f"Error: {ex}"
        lv.controls.append(_bubble(ans, False))
        page.update()

    chat["send"].on_click = send
    inp.on_submit = send

    def open_chat(e=None):
        if chat["dlg"] not in page.overlay:
            page.overlay.append(chat["dlg"])
        chat["dlg"].open = True; page.update()

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.icons.SMART_TOY_OUTLINED, text="Asistente", on_click=open_chat
    )
    return page.floating_action_button

def attach_dashboard_chatbot(page: ft.Page, state):
    """FAB para el dashboard. Inyecta db y conn para comandos como /orden 15 (si los implementaste en chatbot_core)."""
    api = _get_api_key(page)
    if not api:
        page.floating_action_button = ft.FloatingActionButton(text="Asistente", disabled=True,
            tooltip="Falta OpenAI API Key. Configúrala en 'Configurar conexiones'.")
        return

    ctrl = ControladorChatbot(
        estrategia=Modelo4oMini(),
        contexto_inicial="Eres el asistente de la app de órdenes. Responde breve y claro.",
        api_key=api,
        db=state.db,
        conn=state.conn
    )
    chat = _build_dialog(page)
    lv, inp = chat["lv"], chat["inp"]

    def send(_=None):
        t = (inp.value or "").strip()
        if not t: return
        inp.value = ""; lv.controls.append(_bubble(t, True)); page.update()
        try: ans = ctrl.preguntar(t)
        except Exception as ex: ans = f"Error: {ex}"
        lv.controls.append(_bubble(ans, False)); page.update()

    chat["send"].on_click = send
    inp.on_submit = send

    def open_chat(e=None):
        if chat["dlg"] not in page.overlay:
            page.overlay.append(chat["dlg"])
        chat["dlg"].open = True; page.update()

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.icons.SMART_TOY_OUTLINED, text="Asistente", on_click=open_chat
    )

# ---- helpers UI ----
def _bubble(text: str, me: bool) -> ft.Row:
    bg = ft.colors.BLUE_GREY_800 if me else ft.colors.GREY_800
    al = ft.MainAxisAlignment.END if me else ft.MainAxisAlignment.START
    return ft.Row([ft.Container(ft.Text(text, selectable=True), bgcolor=bg, padding=10, border_radius=12, width=520)], alignment=al)

def _build_dialog(page: ft.Page):
    lv  = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=10)
    inp = ft.TextField(expand=True, hint_text="Escribe /probar, /ayuda…", min_lines=1, max_lines=4, multiline=True, border_color=ft.colors.BLUE_GREY_300)
    send= ft.IconButton(icon=ft.icons.SEND)
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.icons.SMART_TOY_OUTLINED), ft.Text("Asistente")], spacing=8),
        content=ft.Container(ft.Column([ft.Row([], spacing=8), ft.Container(lv, height=380), ft.Row([inp, send])], tight=True, spacing=10), width=600, height=500),
        actions=[ft.TextButton("Cerrar", on_click=lambda e: close())],
        on_dismiss=lambda e: close(),
        open=False,
    )
    def close(): dlg.open=False; page.update()
    return {"dlg": dlg, "lv": lv, "inp": inp, "send": send}