import flet as ft
import os
from chatbot_core import ControladorChatbot, Modelo4oMini, Modelo4o
import asyncio

VALID_USER = "cib700_01"
VALID_PASS = "Hector701%/01."

import re

# --- Helpers de validación ---
EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)
PHONE_10_RE = re.compile(r"^\d{10}$")
PHONE_PLUS52_RE = re.compile(r"^\+52\d{10}$")

def normalize_mx_phone_strict(raw: str) -> str | None:
    """
    Acepta:
      - 10 dígitos exactos (e.g. 5512345678)
      - +52 y 10 dígitos (e.g. +525512345678)
    Devuelve siempre los 10 dígitos locales o None si es inválido.
    """
    s = (raw or "").strip()
    if PHONE_10_RE.fullmatch(s):
        return s
    if PHONE_PLUS52_RE.fullmatch(s):
        return s[-10:]  # descarta el +52 y regresa solo 10 dígitos
    return None


def _clean_phone(s: str) -> str:
    """Solo dígitos, normaliza 52xxxxxxxxxx a 10 dígitos finales."""
    ds = "".join(ch for ch in (s or "") if ch.isdigit())
    if len(ds) == 12 and ds.startswith("52"):
        ds = ds[-10:]
    return ds

def _normalize_house(s: str) -> str:
    """Normaliza No. de calle (S/N, 123B, 88-2, etc.)."""
    s = (s or "").strip().upper().replace(" ", "")
    s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
    if s in ("SN", "S-N"):
        s = "S/N"
    return s


def get_openai_api_key(page: ft.Page):
    # 1) si se guardó en almacenamiento local (UI)
    k = page.client_storage.get("openai_api_key")
    if k:
        return k
    # 2) fallback a variable de entorno
    return os.getenv("OPENAI_API_KEY")

# --- Compatibilidad Flet (algunas versiones exponen Colors/Icons con mayúscula) ---
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors  # alias transparente

if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons    # alias transparente
# -----------------------------------------------------------------------------

from utils.config import cargar_datos_conexion, guardar_datos_conexion
from controller.app_controller import AppController

from model.usuario import usuarios_default

# En tu clase de BD / Fachada


def main(page: ft.Page):
    datos = cargar_datos_conexion('conexion_db.txt')

    status = {
        7:"Alta",
        1:"En proceso",
        8:"Terminado",
        9:"Recogido"
    }
    page.title = "Inicio de Sesion"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    login_message = ft.Text("", color="red", text_align=ft.TextAlign.CENTER)

    user_input = ft.TextField(label="Usuario", width=300, text_align=ft.TextAlign.LEFT, border_color=ft.colors.BLUE_300)
    password_input = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300,
                                  text_align=ft.TextAlign.LEFT, border_color=ft.colors.BLUE_300)

    oracle_port = ft.TextField(label="Puerto", width=300, border_color=ft.colors.BLUE_300, value=datos['port'])
    oracle_host = ft.TextField(label="Nombre Host", width=300, border_color=ft.colors.BLUE_300, value=datos['hostname'])
    oracle_service = ft.TextField(label="Nombre del Servicio", width=300, border_color=ft.colors.BLUE_300, value=datos['service_name'])
    mongo_connection = ft.TextField(label="Cadena de Conexión", width=300, multiline=True,
                                    border_color=ft.colors.BLUE_300, max_lines=7, value=datos['mongodb_url'])

    connection_message = ft.Text("", text_align=ft.TextAlign.CENTER)

    openai_api_key_tf = ft.TextField(
        label="OpenAI API Key",
        password=True,
        can_reveal_password=True,
        width=300,
        border_color=ft.colors.BLUE_300,
        value=page.client_storage.get("openai_api_key") or ""
    )


    dialogo_conexiones = ft.AlertDialog(
    title=ft.Text("Configuración de Conexiones"),
    content=ft.Container(
        content=ft.Column(
            [
                ft.Text("Servidor Oracle SQL", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([oracle_port]),
                ft.Row([oracle_host]),
                ft.Row([oracle_service]),

                ft.Divider(height=10, thickness=1),

                ft.Text("Servidor MongoDB", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([mongo_connection]),

                ft.Divider(height=10, thickness=1),

                ft.Text("OpenAI", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([openai_api_key_tf]),

                connection_message,
            ]
        ),
    ),
    actions=[
        ft.ElevatedButton("Guardar", on_click=lambda e: guardar_configuracion()),
        ft.ElevatedButton("Salir", on_click=lambda e: cerrar_dialogo(), color=ft.colors.RED)
    ],
    open=False
)


    dialogo_acerca_de = ft.AlertDialog(
        title=ft.Text("Acerca de"),
        content=ft.Text("Proyecto final \nDiseño y Programación de Bases de datos\nVersión: 1\nIntegrantes: Candelario Sandoval Isai, González Espinosa Héctor Armando\nJaimes Calderón Cesar Daniel, Leyva Durante Adrián Emiliano\nSoto Natera Sebastián \n\nVersión 2.0\nAnálisis y Diseño de Sistemas\nIntegrantes:\nCerdeira Bengoechea Axel\nGonzález Espinosa Héctor Armando\nRuiz Cerdeño Patricio\nSánchez Girón Jorge\n\nVersión 3.0\nArquitectura e Ingeniería de Software\nIntegrantes:\nCerdeira Bengoechea Axel\nGonzález Espinosa Héctor Armando\nRuiz Cerdeño Patricio\nSánchez Girón Jorge"),
        actions=[
            ft.ElevatedButton("Cerrar", on_click=lambda e: cerrar_dialogo_acerca_de(), color=ft.colors.RED)
        ],
        open=False
    )

    def mostrar_dialogo_conexiones(e):
        datos = cargar_datos_conexion('conexion_db.txt')
        oracle_port.value=datos['port']
        oracle_host.value=datos['hostname']
        oracle_service.value=datos['service_name']
        mongo_connection.value=datos['mongodb_url']
        connection_message.value = ""
        openai_api_key_tf.value = get_openai_api_key(page) or ""
        dialogo_conexiones.open = True
        page.update()

    def cerrar_dialogo():
        dialogo_conexiones.open = False
        page.update()

    def mostrar_dialogo_acerca_de(e):
        dialogo_acerca_de.open = True
        page.update()

    def cerrar_dialogo_acerca_de():
        dialogo_acerca_de.open = False
        page.update()


    def guardar_configuracion():
        # 1) Guardar conexiones si están completas
        ok_conn = all([
            (oracle_host.value or "").strip(),
            (oracle_port.value or "").strip(),
            (oracle_service.value or "").strip(),
            (mongo_connection.value or "").strip(),
        ])

        if ok_conn:
            guardar_datos_conexion(
                'conexion_db.txt',
                hostname=oracle_host.value.strip(),
                port=oracle_port.value.strip(),
                service_name=oracle_service.value.strip(),
                mongodb_url=mongo_connection.value.strip()
            )

        # 2) Guardar / limpiar API key local
        api = (openai_api_key_tf.value or "").strip()
        try:
            if api:
                page.client_storage.set("openai_api_key", api)
            else:
                page.client_storage.remove("openai_api_key")
        except Exception as ex:
            print("WARN: no se pudo guardar la API key:", ex)

        # 3) Feedback visual
        if ok_conn:
            connection_message.value = "Información guardada"
            connection_message.color = "green"
        else:
            connection_message.value = "Configure todas las conexiones"
            connection_message.color = "red"

        # 4) Re-crear el FAB del chatbot (se habilita si ya hay API key)
        page.floating_action_button = make_login_chatbot_fab(page)

        page.update()


    def login(e):
        username = (user_input.value or "").strip()
        password = (password_input.value or "").strip()

        # valida credenciales fijas
        if username != VALID_USER or password != VALID_PASS:
            login_message.value = "Usuario o contraseña incorrectos."
            login_button.disabled = False
            loading_indicator.visible = False
            page.update()
            return

        # si llegó aquí, las credenciales son correctas -> conecta a la BD
        controller = AppController()
        try:
            db_instance, connection = controller.connect(
                datos['hostname'], datos['port'], datos['service_name'],
                username=username, password=password
            )
        except Exception:
            db_instance, connection = (None, None)

        if connection is None:
            login_message.value = "No se pudo establecer conexión con la base de datos."
            login_button.disabled = False
            loading_indicator.visible = False
            page.update()
            return

        # éxito: limpia campos y avanza
        user_input.value = ""
        password_input.value = ""
        login_message.value = ""
        login_button.disabled = False
        loading_indicator.visible = False

        usuarios = usuarios_default() or []
        user = next((u for u in usuarios if u.name == username), None) or usuarios[0]

        page.views.append(create_dashboard_view(db_instance, connection, user))
        page.go("/dashboard")
        page.title = "Pagina principal"
        page.update()


    def login_previo(e = None):
        login_message.value=''
        login_button.disabled = True
        loading_indicator.visible = True
        page.update()
        login(e)

    login_button = ft.ElevatedButton("Iniciar Sesión", on_click=lambda e: login_previo(e))

    loading_indicator = ft.ProgressRing( visible=False)

    configurar_conexiones_btn = ft.TextButton("Configurar conexiones", on_click=mostrar_dialogo_conexiones)
    acerca_de_btn = ft.TextButton("Acerca de", on_click=mostrar_dialogo_acerca_de)

    
    def make_login_chatbot_fab(page: ft.Page) -> ft.FloatingActionButton:
        api_key = page.client_storage.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ft.FloatingActionButton(
                icon=ft.icons.SMART_TOY_OUTLINED, text="Asistente",
                disabled=True, tooltip="Configura tu OpenAI API Key en 'Configurar conexiones'."
            )

        ctrl = ControladorChatbot(
            estrategia=Modelo4oMini(),
            contexto_inicial="Eres el asistente del sistema de órdenes. Responde breve y útil.",
            api_key=api_key,
        )

        # UI básica
        chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=10)
        input_field = ft.TextField(hint_text="Escribe tu mensaje…", expand=True, multiline=True, min_lines=1, max_lines=5)

        async def ask(prompt: str):
            chat_list.controls.append(ft.Row([ft.Container(ft.Text(prompt), padding=10, border_radius=12, width=440)], alignment=ft.MainAxisAlignment.END))
            chat_list.controls.append(ft.Row([ft.Container(ft.Text("…"), padding=10, border_radius=12, width=440)], alignment=ft.MainAxisAlignment.START))
            page.update()
            try:
                resp = ctrl.preguntar(prompt)
            except Exception as ex:
                resp = f"Error: {ex}"
            # reemplaza el "…" por la respuesta
            chat_list.controls[-1] = ft.Row([ft.Container(ft.Text(resp), padding=10, border_radius=12, width=440)], alignment=ft.MainAxisAlignment.START)
            page.update()

        async def send_click_async():
            msg = (input_field.value or "").strip()
            if not msg:
                return
            input_field.value = ""
            page.update()
            await ask(msg)

        # IMPORTANTE: definir handlers antes de crear los controles que los referencian
        def send_click(e=None):
            # run_task necesita una función coroutine (no lambda)
            page.run_task(send_click_async)

        # Diálogo
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.SMART_TOY_OUTLINED), ft.Text("Asistente")], spacing=8),
            content=ft.Container(
                content=ft.Column(
                    [chat_list, ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)],
                    expand=True, tight=True, spacing=10
                ),
                width=520, height=420, padding=16,
            ),
            actions=[],  # se setea después
            open=False,
        )

        def close_chat(e=None):
            dlg.open = False
            page.update()

        def open_chat(e=None):
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # Ahora que send_click ya existe, podemos crear el botón y meterlo en el Row:
        send_btn = ft.IconButton(icon=ft.icons.SEND, on_click=send_click)
        dlg.content.content.controls[1].controls = [input_field, send_btn]
        dlg.actions = [ft.TextButton("Cerrar", on_click=close_chat)]
        dlg.on_dismiss = close_chat

        return ft.FloatingActionButton(icon=ft.icons.SMART_TOY_OUTLINED, text="Asistente", on_click=open_chat)

    
    def create_login_view():
        return ft.View(
            "/",
            controls=[
                ft.Row([ft.Container(), configurar_conexiones_btn], alignment=ft.MainAxisAlignment.END),
                ft.Column(
                    [
                        ft.Text("Iniciar Sesión", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        user_input,
                        password_input,
                        login_button,
                        login_message,
                        loading_indicator,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row([ft.Container(), acerca_de_btn], alignment=ft.MainAxisAlignment.END),
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            # 👉 FAB asociado al View (algunas versiones de Flet lo requieren)
            floating_action_button=make_login_chatbot_fab(page),
        )

    def create_dashboard_view(db_instance, connection, user):

        def attach_chatbot_ui():
            # 1) Controlador siguiendo tu UML (estrategia 4o_mini por defecto)
            ctrl = ControladorChatbot(
                Modelo4oMini(),
                contexto_inicial="Eres el asistente de la aplicación de órdenes. Responde en español, breve y claro."
            )

            # 2) UI del chat
            msgs = ft.ListView(expand=True, auto_scroll=True, spacing=8, padding=10)

            def bubble(who: str, text: str) -> ft.Row:
                is_user = who == "yo"
                bg = ft.colors.BLUE_GREY_800 if is_user else ft.colors.GREY_800
                align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
                return ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(text, selectable=True, size=14),
                            bgcolor=bg,
                            padding=10,
                            border_radius=12,
                            width=420,
                        )
                    ],
                    alignment=align,
                )

            chips = ft.Row(spacing=8)

            # Cambiar modelo on-the-fly (Strategy)
            model_dd = ft.Dropdown(
                width=150,
                value="4o-mini",
                options=[ft.dropdown.Option("4o-mini"), ft.dropdown.Option("4o")],
            )
            def on_model_change(e):
                if model_dd.value == "4o":
                    ctrl.cambiarmodelo(Modelo4o())
                else:
                    ctrl.cambiarmodelo(Modelo4oMini())
            model_dd.on_change = on_model_change

            inp = ft.TextField(
                hint_text="Escribe tu mensaje…",
                expand=True,
                on_submit=lambda e: send_msg(),
            )
            send_btn = ft.IconButton(ft.icons.SEND, on_click=lambda e: send_msg())

            sending = False
            def send_msg():
                nonlocal sending
                if sending:
                    return
                t = (inp.value or "").strip()
                if not t:
                    return
                inp.value = ""
                msgs.controls.append(bubble("yo", t))
                page.update()

                try:
                    sending = True
                    turno = ctrl.enviarmensaje(t)  # llamada a OpenAI
                    answer = turno[-1]["content"]
                    msgs.controls.append(bubble("bot", answer))

                    # métricas desde decoradores (Latencia, Tokens)
                    m = ctrl.metricas
                    chips.controls.clear()
                    chips.controls.extend([
                        ft.Chip(label=ft.Text(m.get("modelo","?"))),
                        ft.Chip(label=ft.Text(f'{m.get("lat_ms",0)} ms')),
                        ft.Chip(label=ft.Text(f'{m.get("tokens_aprox",0)} tok')),
                    ])
                finally:
                    sending = False
                    page.update()

            dialog_body = ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Chatbot", size=18, weight=ft.FontWeight.BOLD),
                                model_dd
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        chips,
                        ft.Divider(),
                        ft.Container(msgs, height=380),
                        ft.Row([inp, send_btn]),
                    ],
                    tight=True,
                ),
                width=540,
                padding=10,
            )

            dlg_chat = ft.AlertDialog(
                modal=True,
                content=dialog_body,
                actions=[ft.TextButton("Cerrar", on_click=lambda e: close_chat())],
            )

            def open_chat(e=None):
                if dlg_chat not in page.overlay:
                    page.overlay.append(dlg_chat)
                dlg_chat.open = True
                page.update()

            def close_chat():
                dlg_chat.open = False
                page.update()

            # 3) Botón flotante (abajo-derecha)
            page.floating_action_button = ft.FloatingActionButton(
                icon=ft.icons.CHAT,
                text="Chat",
                on_click=open_chat
            )

        # …al final de create_dashboard_view, después de construir tu tablero:
        attach_chatbot_ui()

        # === Helpers de STATUS (DEFINIRLOS ANTES DE USARLOS) ===

        # --- helpers de estado (deben ir antes de usarlos) ---
        def _load_status_catalog():
            try:
                filas = db_instance.statuses()  # [(1,'En proceso'), (2,'Terminada'), (3,'Recogida')] o dicts
            except Exception:
                filas = None
            cat = {}
            if filas:
                for it in filas:
                    if isinstance(it, dict):
                        k = it.get("cve_status") or it.get("id")
                        v = it.get("descripcion") or it.get("nombre")
                    else:
                        k, v = it[0], it[1]
                    try:
                        k = int(str(k).strip())
                    except Exception:
                        continue
                    cat[k] = str(v or "").strip()
            if not cat:
                cat = {1: "En proceso", 2: "Terminada", 3: "Recogida"}
            return cat

        def _status_chip(nombre_ui: str):
            color = {
                "En proceso": ft.colors.AMBER,
                "Terminado":  ft.colors.GREEN,    # la UI puede decir "Terminado"
                "Terminada":  ft.colors.GREEN,    # en BD es "Terminada"
                "Recogido":   ft.colors.INDIGO_200,
                "Recogida":   ft.colors.INDIGO_200,
            }.get(nombre_ui, ft.colors.AMBER)
            return ft.Container(
                content=ft.Text(nombre_ui, weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10, bgcolor=color, width=100, alignment=ft.alignment.center, height=30
            )

        def _update_orden_base(conn, orden_id, marca, tipo_id, modelo, status_id):
            cur = conn.cursor()
            print("DEBUG status_id:", status_id, "status_cat:", status_cat)
            print("DEBUG STATUS->", dict(
    marca=marca, tipo_id=int(tipo_id), modelo=modelo, status_id=int(status_id), ord=int(orden_id)
))
            cur.execute(
                """
                UPDATE orden
                SET eq_marca        = :marca,
                    cve_tipo_equipo = :tipo_id,
                    eq_modelo       = :modelo,
                    cve_status      = :status_id
                WHERE cve_orden       = :ord
                """,
                dict(
                    marca=marca,
                    tipo_id=int(tipo_id),
                    modelo=modelo,
                    status_id=int(status_id),
                    ord=int(orden_id),
                ),
            )

        def _status_id_from_control(value_from_ui, status_cat):
            """
            Acepta: '2' | 2 | 'Terminada' | 'Terminado' etc. y devuelve el id válido (1/2/3) o None.
            """
            if isinstance(value_from_ui, int):
                return value_from_ui
            s = ("" if value_from_ui is None else str(value_from_ui)).strip()
            if s.isdigit():
                return int(s)
            s_low = s.lower()
            inv = { (v or "").strip().lower(): k for k, v in status_cat.items() }
            # tolera masculino/femenino en UI
            if s_low == "terminado": s_low = "terminada"
            if s_low == "recogido":  s_low = "recogida"
            return inv.get(s_low)


        def _normalize_status(name: str) -> str:
            s = (name or "").strip().lower()
            if s in ("en proceso", "en proceso."):
                return "En proceso"
            if s in ("terminada", "terminado"):
                return "Terminado"
            if s in ("recogida", "recogido"):
                return "Recogido"
            return (name or "").strip()

        def _status_chip(nombre_ui: str):
            color = {
                "En proceso": ft.colors.AMBER,
                "Terminado":  ft.colors.GREEN,
                "Recogido":   ft.colors.INDIGO_200,
            }.get(nombre_ui, ft.colors.AMBER)
            return ft.Container(
                content=ft.Text(nombre_ui, weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=color,
                width=100,
                alignment=ft.alignment.center,
                height=30,
            )
        status_cat = _load_status_catalog()  # {id:int -> nombre:str}

        # --- Cargar catálogo de estatus directamente de BD (sin hardcode) ---
        def _status_catalog_from_db():
            try:
                filas = db_instance.statuses()     # [{'cve_status':1,'descripcion':'En proceso'}, ...] o tu shape
            except Exception:
                filas = None

            if filas:
                cat = {}
                for it in filas:
                    if isinstance(it, dict):
                        k = it.get("cve_status") or it.get("id")
                        v = it.get("descripcion") or it.get("nombre") or it.get("status")
                    elif isinstance(it, (list, tuple)) and len(it) >= 2:
                        k, v = it[0], it[1]
                    else:
                        continue
                    try:
                        k = int(str(k).strip())
                    except Exception:
                        continue
                    cat[k] = str(v or "").strip()
                if cat:
                    return cat

            # Fallback a tu dict local ‘status’ (id->nombre)
            return dict(status)

        def _normalize_status(name: str) -> str:
            s = (name or "").strip().lower()
            if s in ("en proceso", "en proceso."):
                return "En proceso"
            if s in ("terminada", "terminado"):
                return "Terminado"
            if s in ("recogida", "recogido"):
                return "Recogido"
            return (name or "").strip()  # fallback (tal cual venga)
        



        # Cárgalo una vez al entrar al dashboard
        status_cat = _status_catalog_from_db()


        def _status_chip(nombre: str):
            nombre = (nombre or "").strip()
            c = ft.colors
            colores = {
                "Alta": c.LIGHT_BLUE_200,
                "En proceso": c.AMBER,
                "Terminado": c.GREEN,
                "Recogido": c.INDIGO_200,
            }
            return ft.Container(
                content=ft.Text(nombre, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                border_radius=10,
                bgcolor=colores.get(nombre, c.GREY_300),
                width=100,
                height=30,
                alignment=ft.alignment.center,
            )


        # Cargar catálogo inicial
        status_cat = _status_catalog_from_db()
        # === Fin helpers STATUS ===            

        def _actualizar_horas_orden(cve_orden: int, horas: int) -> None:
            """
            Sube 'horas' a ORDEN_TECNICOS de la orden dada.
            Si hay varios técnicos, actualiza solo el primero (no duplica).
            """
            cur = connection.cursor()
            cur.execute(
                """
                UPDATE orden_tecnicos ot
                SET ot.horas = :horas
                WHERE ot.cve_orden = :ord
                AND ot.cve_empleado = (
                        SELECT cve_empleado
                        FROM orden_tecnicos
                        WHERE cve_orden = :ord
                        FETCH FIRST 1 ROWS ONLY
                )
                """,
                dict(horas=int(horas), ord=int(cve_orden)),
            )
        # Colócalo al inicio de create_dashboard_view(...) o encima de guardar_cambios()
        STATUS_LABEL_TO_ID = {
            "alta": 7,
            "en proceso": 1,
            "terminado": 8, "terminada": 8,   # por si en algún lugar tienes el femenino
            "recogido": 9,  "recogida": 9,
        }
        permisos = user.permisos()
        ordenes = db_instance.ordenes()

        def _update_status_direct(cve_orden: int, status_id: int) -> None:
            """Actualiza el status directo en la tabla de órdenes (por si el método guardar no lo hizo)."""
            cur = connection.cursor()
            cur.execute(
                "UPDATE orden SET cve_status = :sid WHERE cve_orden = :ord",
                dict(sid=int(status_id), ord=int(cve_orden)),
            )
        # Carga catálogo inicial
        status_cat = _status_catalog_from_db()

        # --- Catálogo STATUS (id -> nombre) cacheado para pintar/filtrar ---
        def _status_catalog_from_db():
            try:
                cur = connection.cursor()
                cur.execute("SELECT cve_status, status FROM status")
                return {int(i): (n or "").strip() for (i, n) in cur.fetchall()}
            except Exception:
                return {}

        status_cat = _status_catalog_from_db()  # <- crea el binding en el scope exterior

        def logout(e):
            page.title = "Inicio de Sesion"
            db_instance.close_connection()
            page.views.pop()
            page.go("/")
        
        def _status_catalog_from_db():
            """
            Lee el catálogo real de estatus desde BD y devuelve {id:int -> nombre:str}.
            Si falla, usa el dict local 'status' (id->texto) que ya tienes.
            """
            try:
                filas = db_instance.statuses()   # ajusta al método real de tu fachada
            except Exception:
                filas = None

            if filas:
                cat = {}
                for it in filas:
                    if isinstance(it, dict):
                        k = it.get("cve_status") or it.get("id")
                        v = it.get("descripcion") or it.get("nombre") or it.get("status")
                    elif isinstance(it, (list, tuple)) and len(it) >= 2:
                        k, v = it[0], it[1]
                    else:
                        continue
                    try:
                        k = int(str(k).strip())
                    except Exception:
                        continue
                    cat[k] = str(v or "").strip()
                if cat:
                    return cat

            # Fallback: tu dict local declarado arriba en la vista (id -> texto)
            return dict(status)
        
        status_cat = _status_catalog_from_db()  # {id:int -> nombre:str}

        def _normalize_status(name: str) -> str:
            s = (name or "").strip().lower()
            if s in ("en proceso", "en proceso."):
                return "En proceso"
            if s in ("terminada", "terminado"):
                return "Terminado"
            if s in ("recogida", "recogido"):
                return "Recogido"
            return (name or "").strip()

        def refresh_status_cache():
            nonlocal status_cat
            status_cat = _status_catalog_from_db()

        def _update_orden_base(conn, orden_id, marca, tipo_id, modelo, status_id):
            cur = conn.cursor()
            # DEBUG opcional: imprime lo que se mandará a Oracle
            # print("UPDATE orden cve_orden=", orden_id, " status_id=", status_id, " tipo_id=", tipo_id)
            cur.execute(
                """
                UPDATE orden
                SET eq_marca        = :marca,
                    cve_tipo_equipo = :tipo_id,
                    eq_modelo       = :modelo,
                    cve_status      = :status_id
                WHERE cve_orden       = :ord
                """,
                dict(
                    marca=marca,
                    tipo_id=int(tipo_id),
                    modelo=modelo,
                    status_id=int(status_id),
                    ord=int(orden_id),
                ),
            )


        def _status_id_from_ui(value_from_ui):
            """
            Convierte lo que viene del RadioGroup a un id válido,
            comparando contra el catálogo real (case-insensitive).
            """
            if isinstance(value_from_ui, int):
                return value_from_ui

            s = ("" if value_from_ui is None else str(value_from_ui)).strip()
            if s.isdigit():
                return int(s)

            cat = _status_catalog_from_db()             # {id:int -> nombre:str}
            inv = { (v or "").strip().lower(): k for k, v in cat.items() }  # {nombre->id}

            return inv.get(s.lower(), None)  # None si no existe
        
        def _get_status_id(valor):
            # acepta int o str ("Terminado", "En proceso", etc.)
            if isinstance(valor, int):
                return valor
            s = ("" if valor is None else str(valor)).strip().lower()

            try:
                # trae (id, nombre) de la tabla STATUS, como sea que tu db_instance lo devuelva
                rows = db_instance.statuses()  # ideal: [('1','Terminado'), ...] o [{'CVE_STATUS':1,'STATUS':'Terminado'}]
            except Exception:
                # fallback genérico: haz la consulta cruda si no tienes helper
                rows = db_instance.select("SELECT cve_status, status FROM status")

            for r in rows or []:
                if isinstance(r, dict):
                    name = str(r.get("status") or r.get("STATUS") or "").strip().lower()
                    sid  = r.get("cve_status") or r.get("CVE_STATUS")
                else:
                    sid, name = (r[0], str(r[1]).strip().lower())
                if name == s:
                    return int(sid)

            return None  # no existe en catálogo

        # -- Helper único para refrescar la tabla sin romper por la firma --
        def refrescar_tabla():
            try:
                # Firma nueva (con 4 args)
                llenar_tabla_ordenes(
                    filtro_estado=filtro_estado.value,
                    filtro_direccion=filtro_direccion.selected,
                    filtro_taller=filtro_taller.value,
                    recargar=True,
                )
            except TypeError:
                # Por si tu firma aún fuera la vieja, mantenemos compatibilidad
                llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, True)

        def _get_tipo_id(valor_tipo):
            """Acepta int, str, dict o tupla del catálogo y devuelve el id de tipo."""
            if isinstance(valor_tipo, int):
                return valor_tipo
            s = ("" if valor_tipo is None else str(valor_tipo)).strip()
            if s.isdigit():
                return int(s)

            # Catálogo devuelto por la BD (puede ser lista de dicts o de tuplas)
            try:
                tipos = db_instance.tipos() or []
            except Exception:
                tipos = []

            def _tomar_id(item):
                if isinstance(item, dict):
                    for k in ("cve_tipo_equipo", "id", "cve"):
                        if k in item and str(item[k]).strip().isdigit():
                            return int(item[k])
                elif isinstance(item, (list, tuple)):
                    # típico (id, descripcion, ...)
                    if len(item) > 0 and str(item[0]).strip().isdigit():
                        return int(item[0])
                return None

            def _tomar_nombre(item):
                if isinstance(item, dict):
                    for k in ("descripcion", "nombre", "tipo"):
                        if k in item:
                            return str(item[k]).strip().lower()
                elif isinstance(item, (list, tuple)):
                    if len(item) > 1:
                        return str(item[1]).strip().lower()
                return ""

            s_low = s.lower()
            for it in tipos:
                if _tomar_nombre(it) == s_low:
                    _id = _tomar_id(it)
                    if _id is not None:
                        return _id

            # No encontrado → devolvemos el texto; el modelo/BD fallará si no es válido
            return s 
        
        
        
        def _actualizar_horas_orden(cve_orden: int, horas: int) -> None:
            """
            Sube 'horas' a ORDEN_TECNICOS para la orden dada.
            Si hay varios técnicos, actualiza solo el primero.
            """
            cur = connection.cursor()
            cur.execute(
                """
                UPDATE orden_tecnicos ot
                SET ot.horas = :horas
                WHERE ot.cve_orden = :ord
                AND ot.cve_empleado = (
                        SELECT cve_empleado
                        FROM orden_tecnicos
                        WHERE cve_orden = :ord
                        FETCH FIRST 1 ROWS ONLY
                )
                """,
                dict(horas=int(horas), ord=int(cve_orden)),
            )
            # Si no hay técnico, rowcount puede ser 0: no es error.


        def guardar_cambios(orden, numero, marca, tipo, modelo, stat):
            """
            Guarda marca/tipo/modelo/status y horas de una orden
            'stat' llega del RadioGroup como '1'|'2'|'3' (o int); 'numero' = horas.
            """
            try:
                nonlocal status_cat, ordenes  # vamos a refrescar catálogo y órdenes

                # --- Tipo a id ---
                tipo_id = _get_tipo_id(tipo)

                # --- Status a id (int) ---
                if isinstance(stat, int) or (isinstance(stat, str) and stat.isdigit()):
                    status_id = int(stat)
                else:
                    s = str(stat or "").strip().lower()
                    inv = {(v or "").strip().lower(): int(k) for k, v in status_cat.items()}
                    status_id = inv.get(s, int(orden.cve_status))  # fallback al actual

                # --- UPDATE ORDEN (evitamos la firma de model.orden.guardar) ---
                cur = connection.cursor()

                # DEBUG opcional:
                # print("UPDATE ORDEN:", dict(marca=marca, tipo_id=int(tipo_id), modelo=modelo,
                #                             status_id=int(status_id), ord=int(orden.cve_orden)))

                cur.execute(
                    """
                    UPDATE orden
                    SET eq_marca        = :marca,
                        cve_tipo_equipo = :tipo_id,
                        eq_modelo       = :modelo,
                        cve_status      = :status_id
                    WHERE cve_orden       = :ord
                    """,
                    dict(
                        marca=marca,
                        tipo_id=int(tipo_id),
                        modelo=modelo,
                        status_id=int(status_id),
                        ord=int(orden.cve_orden),
                    ),
                )

                # --- Horas en ORDEN_TECNICOS ---
                try:
                    _actualizar_horas_orden(int(orden.cve_orden), int(numero))
                except Exception as e:
                    print("WARN horas:", e)

                connection.commit()

                # --- Refrescar catálogo y tabla desde BD ---
                status_cat = _status_catalog_from_db()
                ordenes = db_instance.ordenes()
                llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, actualizar=True)

                page.open(ft.SnackBar(ft.Text("Orden actualizada con éxito")))
                page.update()

            except Exception as ex:
                try:
                    connection.rollback()
                except Exception:
                    pass
                page.open(ft.SnackBar(ft.Text(f"Error al actualizar la orden: {ex}")))

        def cerrar_dialogo_edicion(e=None):
            for dialog in page.overlay:
                if isinstance(dialog, ft.AlertDialog) and dialog.open:
                    dialog.open = False
                    llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value)
                    refrescar_tabla()
                    page.update()
                    break

        def resumir(orden):
            return str(orden.cve_orden) + " " + orden.eq_modelo + " " + str(orden.cliente)

        def ver_tecnico(lista):
            if len(lista) == 1:
                return lista[0]
            return lista[0] + "..."

        def _status_catalog_from_db():
            """Devuelve {id:int -> nombre:str} desde STATUS; fallback a tu dict `status`."""
            try:
                filas = db_instance.statuses()
            except Exception:
                filas = None

            cat = {}
            if filas:
                for it in filas:
                    if isinstance(it, dict):
                        k = it.get("cve_status") or it.get("id")
                        v = it.get("descripcion") or it.get("nombre") or it.get("status")
                    elif isinstance(it, (list, tuple)) and len(it) >= 2:
                        k, v = it[0], it[1]
                    else:
                        continue
                    try:
                        k = int(str(k).strip())
                    except Exception:
                        continue
                    cat[k] = str(v or "").strip()
            if cat:
                return cat
            # Fallback a tu dict local `status`
            return {1: "En proceso", 2: "Terminada", 3: "Recogida"}

        # Cárgalo una vez (scope de create_dashboard_view):
        status_cat = _status_catalog_from_db()

        def _actualizar_horas_orden(cve_orden: int, horas: int) -> None:
            cur = connection.cursor()
            cur.execute(
                """
                UPDATE orden_tecnicos ot
                SET ot.horas = :horas
                WHERE ot.cve_orden = :ord
                AND ot.cve_empleado = (
                        SELECT cve_empleado
                        FROM orden_tecnicos
                        WHERE cve_orden = :ord
                        FETCH FIRST 1 ROWS ONLY
                )
                """,
                dict(horas=int(horas), ord=int(cve_orden)),
            )

        def abrir_dialogo_edicion(orden):
            def cerrar():
                cerrar_dialogo_edicion()

            txt_number = ft.TextField(value=str(orden.horas), text_align=ft.TextAlign.RIGHT, width=100)

            def _parse_int_hours(val):
                try:
                    s = str(val).replace(",", ".").strip()
                    return int(float(s))
                except Exception:
                    return 0

            def plus_click(e):
                txt_number.value = str(_parse_int_hours(txt_number.value) + 1)
                page.update()

            def minus_click(e):
                v = _parse_int_hours(txt_number.value) - 1
                if v < 0:
                    v = 0
                txt_number.value = str(v)
                page.update()

            marca = ft.TextField(label="Marca", value=orden.eq_marca, expand=True, width=300)

            tipos = db_instance.tipos()
            campo_tipo = ft.Dropdown(
                label="Tipo",
                options=[ft.dropdown.Option(text=tipos[t][1], key=t) for t in tipos.keys()],
                expand=True,
                value=orden.cve_tipo_equipo,
            )

            modelo = ft.TextField(label="Modelo", value=orden.eq_modelo, expand=True, width=300)

            # Orden sugerido de visualización
            orden_visual = ["Alta", "En proceso", "Terminado", "Recogido"]
            ids_por_nombre = {v: k for k, v in status_cat.items()}

            ordered_ids = [ids_por_nombre[n] for n in orden_visual if n in ids_por_nombre] \
                        + [k for k in sorted(status_cat) if status_cat[k] not in orden_visual]

            status_sel = ft.RadioGroup(
                content=ft.Column([ft.Radio(value=str(i), label=status_cat[i]) for i in ordered_ids]),
                value=str(int(orden.cve_status)),
)

            status_sel = ft.RadioGroup(
                content=ft.Column([ft.Radio(value=str(i), label=status_cat[i]) for i in ordered_ids]),
                value=str(int(orden.cve_status)),
            )

            dialogo_edicion = ft.AlertDialog(
                title=ft.Text(f"Editar Orden #{orden.cve_orden}"),
                content=ft.Column(
                    [
                        marca,
                        campo_tipo,
                        modelo,
                        ft.Text(value='Estado de la orden'),
                        status_sel,
                        ft.Text(value='Horas trabajadas'),
                        ft.Row(
                            [
                                ft.IconButton(ft.icons.REMOVE, on_click=minus_click),
                                txt_number,
                                ft.IconButton(ft.icons.ADD, on_click=plus_click),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        )
                    ]
                ),
                actions=[
                    ft.ElevatedButton(
                        "Guardar",
                        on_click=lambda e: guardar_cambios(
                            orden,
                            _parse_int_hours(txt_number.value),
                            marca.value,
                            campo_tipo.value,     # dropdown da id válido
                            modelo.value,
                            status_sel.value,     # <-- id "1"/"2"/"3"
                        ),
                    ),
                    ft.ElevatedButton("Cancelar", on_click=lambda e: cerrar(), color=ft.colors.RED),
                ],
                open=True
            )
            page.overlay.append(dialogo_edicion)
            page.update()


        def abrir_dialogo_edicion_cliente(cliente, cve):
            # --- Campos ---
            nombre   = ft.TextField(label="Nombre",           expand=True, width=300, value=cliente.nombre)
            paterno  = ft.TextField(label="Apellido paterno", expand=True, width=300, value=cliente.paterno)
            materno  = ft.TextField(label="Apellido materno", expand=True, width=300, value=cliente.materno)
            correo   = ft.TextField(label="Correo",           expand=True, width=300, value=cliente.correo, hint_text="ej. usuario@dominio.com")
            telefono = ft.TextField(label="Telefono",         expand=True, width=300, value=cliente.telefono,  hint_text="10 dígitos")
            calle    = ft.TextField(label="Calle",            expand=True, width=300, value=cliente.dir_calle)
            num_calle= ft.TextField(label="No. Calle",        expand=True, width=300, value=cliente.dir_num,   hint_text="1–6 dígitos, opcional letra (123B) o S/N")

            error = ft.Text("", text_align=ft.TextAlign.CENTER, color=ft.colors.RED)

            # --- Validación en vivo ---
            def _val_email_live(e=None):
                txt = (correo.value or "").strip()
                correo.error_text = None if (txt and EMAIL_RE.match(txt)) else "Correo no válido"
                page.update()

            def _val_phone_live(e=None):
                raw = (telefono.value or "").strip()
                ok = PHONE_10_RE.fullmatch(raw) or PHONE_PLUS52_RE.fullmatch(raw)
                telefono.error_text = None if ok else "Use 10 dígitos o +52 y 10 dígitos"
                page.update()

            telefono.on_change = _val_phone_live
            telefono.hint_text = "10 dígitos o +52 y 10 dígitos"

            def _val_house_live(e=None):
                val = _normalize_house(num_calle.value)
                # si no quieres auto-normalizar en vivo, comenta la siguiente línea
                num_calle.value = val
                ok = bool(val and HOUSE_RE.match(val))
                num_calle.error_text = None if ok else "Use 1–6 dígitos, opcional letra (p.ej. 123B) o 'S/N'"
                page.update()

            correo.on_change    = _val_email_live
            telefono.on_change  = _val_phone_live
            num_calle.on_change = _val_house_live

            # --- Guardar con validaciones ---
            def guardar_cliente(e=None):
                error.value = ""
                correo.error_text   = None
                telefono.error_text = None
                num_calle.error_text= None

                nom   = (nombre.value or "").strip()
                pat   = (paterno.value or "").strip()
                mat   = (materno.value or "").strip()
                mail  = (correo.value or "").strip()
                tel_r = telefono.value or ""
                cal   = (calle.value or "").strip()
                num_r = (num_calle.value or "").strip()

                # Obligatorios básicos
                if not all([nom, pat, mail, tel_r, cal, num_r]):
                    error.value = "Llene todos los campos obligatorios."
                    page.update()
                    return

                # Correo
                if not EMAIL_RE.match(mail):
                    correo.error_text = "Correo no válido"
                    error.value = "Corrija los campos marcados en rojo."
                    page.update()
                    return

                # Teléfono (normalizado a 10 dígitos)
                tel_norm = normalize_mx_phone_strict(tel_r)
                if tel_norm is None:
                    telefono.error_text = "Teléfono inválido: 10 dígitos o +52 y 10 dígitos"
                    error.value = "Corrija los campos marcados en rojo."
                    page.update()
                    return

                # No. Calle
                num_norm = _normalize_house(num_r)
                if not HOUSE_RE.match(num_norm):
                    num_calle.error_text = "Número inválido (1–6 dígitos, opcional letra o 'S/N')"
                    error.value = "Corrija los campos marcados en rojo."
                    page.update()
                    return
                num_calle.value = num_norm  # usar el normalizado

                try:
                    # Guarda usando los valores normalizados
                    cliente.guardar(
                        db_instance,
                        nom, pat, mat, mail, tel_norm,  # tel normalizado
                        cal, num_norm
                    )
                    # refresca UI
                    try:
                        llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, True)
                    except Exception:
                        pass
                    cerrar_dialogo_edicion()
                    page.open(ft.SnackBar(ft.Text("Cliente actualizado con éxito")))
                    page.update()
                except Exception as ex:
                    error.value = f"Error al guardar: {ex}"
                    page.update()

            dialogo_edicion = ft.AlertDialog(
                title=ft.Text(f"Editar Cliente Orden #{cve}"),
                content=ft.Column(
                    [nombre, paterno, materno, correo, telefono, calle, num_calle, error]
                ),
                actions=[
                    ft.ElevatedButton("Guardar", on_click=guardar_cliente),
                    ft.ElevatedButton("Cancelar", on_click=cerrar_dialogo_edicion, color=ft.colors.RED),
                ],
                open=True,
            )
            page.overlay.append(dialogo_edicion)
            page.update()

        seccion_nota = ft.Column(
            [
                ft.Text("Nota", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nueva", on_click=lambda e: abrir_dialogo_nueva_nota(), visible=permisos['Nueva_Nota']),
                        ft.ElevatedButton("Ver", on_click=lambda e:abrir_dialogo_notas(), visible=permisos['Ver_Nota'])
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            ]
        )


        def abrir_dialogo_nueva_nota(e=None):

            def guardar():
                if campo_nota.value and ordenes_dropdown.value:
                    cerrar_dialogo_edicion()
                    db_instance.insertar_nota(nota=campo_nota.value, cve_orden=ordenes_dropdown.value)
                    connection.commit()
                    refrescar_tabla()
                    page.open(ft.SnackBar(ft.Text('Nota agregada con exito')))
                    page.update()
                else:
                    error.value = 'Rellene todos los campos'
                    page.update()

            campo_nota = ft.TextField(
                label="Escriba la nota aquí:",
                multiline=True,
                expand=True,
                width=400
            )

            ordenes_dropdown = ft.Dropdown(
                options=[ft.dropdown.Option(text=resumir(orden), key=orden.cve_orden) for orden in ordenes],
                label="Seleccione la orden de la nota",
                value=None
            )
            error = ft.Text('', color=ft.colors.RED)

            dialogo_nueva_nota = ft.AlertDialog(
                content=ft.Column(
                    [
                        ft.Text("Nueva Nota", size=20, weight=ft.FontWeight.BOLD),
                        campo_nota,
                        ordenes_dropdown,
                        error,
                        ft.Row(
                            [
                                ft.ElevatedButton("Agregar", on_click=lambda e: guardar()),
                                ft.ElevatedButton("Cancelar", on_click=lambda e: cerrar_dialogo_edicion(), color=ft.colors.RED)
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),

                    ],
                    spacing=10,
                    height=300
                ),
                open=True,
                alignment=ft.alignment.center
            )

            page.overlay.append(dialogo_nueva_nota)
            page.update()

        nota_contenedor = ft.Container(
            content=seccion_nota,
            border_radius=5,
            padding=20,
            bgcolor=ft.colors.LIGHT_BLUE_600,
            width=300
        )

        if not permisos['Nueva_Nota'] and not permisos['Ver_Nota']:
            nota_contenedor.visible = False

        encabezado_tabla = ft.Row(
            [
                ft.Text("Clave Orden", width=50, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Status", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Tecnico", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text(" ", width=50, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Marca", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Modelo", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Tipo", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Cliente", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Editar Cliente", width=100, size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Editar Orden", width=100, size=15, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        _seen = set()
        ui_statuses = []
        for raw in status_cat.values():
            n = _normalize_status(raw)
            if n not in _seen:
                _seen.add(n)
                ui_statuses.append(n)

        filtro_estado = ft.Dropdown(
            options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(s) for s in ui_statuses],
            value="Todos",
            label="Filtrar ordenes por Status",
            on_change=lambda e: llenar_tabla_ordenes(
                filtro_estado.value, filtro_direccion.selected, filtro_taller.value
            ),
        )
        talleres = db_instance.talleres()

        filtro_taller = ft.Dropdown(label="Filtrar ordenes por Taller",
                                    options=[ft.dropdown.Option(text=talleres[tal], key=tal) for tal in
                                               talleres.keys()],
                                    on_change=lambda e: llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, True)(filtro_estado.value, filtro_direccion.selected, filtro_taller.value))
        filtro_taller.options.insert(0, ft.dropdown.Option(text='Todos', key='0'))
        filtro_taller.value = '0'

        def toggle_icon_button(e):
            e.control.selected = not e.control.selected
            e.control.update()
            llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, True)(filtro_estado.value, filtro_direccion.selected, filtro_taller.value)

        filtro_direccion = ft.IconButton(
            icon=ft.icons.ARROW_DOWNWARD,
            selected_icon = ft.icons.ARROW_UPWARD,
            on_click = toggle_icon_button,
            selected = False,
        )
        filtros = ft.Row(
            [
                filtro_estado,
                filtro_taller,
                filtro_direccion
            ],
        )

        contenedor_ordenes = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )


        status_boton={
            'Alta': ft.Container(
                content=ft.Text("Alta", weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=ft.colors.LIGHT_BLUE_200,
                width=100,
                alignment=ft.alignment.center,
                height=30
            ),
            'En proceso': ft.Container(
                content=ft.Text("En proceso", weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=ft.colors.AMBER,
                width=100,
                alignment=ft.alignment.center,
                height=30
            ),
            'Terminado': ft.Container(
                content=ft.Text("Terminado", weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=ft.colors.GREEN,
                width=100,
                alignment=ft.alignment.center,
                height=30
            ),
            'Recogido': ft.Container(
                content=ft.Text("Recogido", weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=ft.colors.INDIGO_200,
                width=100,
                alignment=ft.alignment.center,
                height=30
            ),
        }

        def _status_chip(nombre_ui: str):
            # Colores por estado ya normalizado
            color = {
                "En proceso": ft.colors.AMBER,
                "Terminado":  ft.colors.GREEN,
                "Recogido":   ft.colors.INDIGO_200,
            }.get(nombre_ui, ft.colors.AMBER)

            return ft.Container(
                content=ft.Text(nombre_ui, weight=ft.FontWeight.BOLD, text_align=ft.alignment.center),
                border_radius=10,
                bgcolor=color,
                width=100,
                alignment=ft.alignment.center,
                height=30,
            )

        
        def llenar_tabla_ordenes(filtro_estado, cambio_dir, filtro_taller, actualizar=False):
            nonlocal ordenes, status_cat  # 'ordenes' y 'status_cat' viven en el scope exterior

            # Si pides recargar, vuelve a leer órdenes y catálogo de status desde BD
            if actualizar:
                ordenes = db_instance.ordenes()
                status_cat = _status_catalog_from_db()

            # Normalizador de nombre de status para que coincida con las llaves de tu UI
            def _ui_status_name(name_or_id):
                # Convierte id->nombre con el catálogo; si ya es texto, lo normaliza
                try:
                    sid = int(name_or_id)
                    raw = status_cat.get(sid, str(sid))
                except Exception:
                    raw = str(name_or_id or "")
                s = raw.strip().lower()
                mapping = {
                    "alta": "Alta",
                    "en proceso": "En proceso",
                    "en progreso": "En proceso",
                    "terminado": "Terminado",
                    "terminada": "Terminado",
                    "recogido": "Recogido",
                    "recogida": "Recogido",
                }
                # Si ya viene exactamente como lo espera la UI, respétalo
                if raw in ("Alta", "En proceso", "Terminado", "Recogido"):
                    return raw
                return mapping.get(s, "En proceso")

            contenedor_ordenes.controls.clear()
            data = ordenes if not cambio_dir else list(reversed(ordenes))

            for o in data:
                nombre_status_ui = _ui_status_name(o.cve_status)

                # Filtros
                pasa_estado = (filtro_estado == "Todos") or (nombre_status_ui == filtro_estado)
                pasa_taller = (str(filtro_taller) == "0") or (str(o.cve_taller) == str(filtro_taller))
                if not (pasa_estado and pasa_taller):
                    continue

                fila_orden = ft.Row(
                    [
                        ft.Text(str(o.cve_orden), width=50),
                        _status_chip(nombre_status_ui),  # <- chip dinámico por estado (¡ya no chip_status!)
                        ft.Text(ver_tecnico(o.tecnicos), width=100),
                        ft.IconButton(
                            icon=ft.icons.REMOVE_RED_EYE,
                            on_click=lambda e, ord=o: abrir_dialogo_tecnicos_taller(ord),
                            width=50,
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(o.eq_marca, width=100),
                        ft.Text(o.eq_modelo, width=100),
                        ft.Text(db_instance.tipos()[o.cve_tipo_equipo][1], width=100),
                        ft.Text(str(o.cliente), width=100),
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            on_click=lambda e, ord=o: abrir_dialogo_edicion_cliente(ord.cliente, o.cve_orden),
                            width=100,
                            alignment=ft.alignment.center,
                        ),
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            on_click=lambda e, ord=o: abrir_dialogo_edicion(ord),
                            width=100,
                            alignment=ft.alignment.center,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    height=50,
                )
                contenedor_ordenes.controls.append(fila_orden)
                contenedor_ordenes.controls.append(ft.Divider())

            page.update()


        llenar_tabla_ordenes('Todos', False, '0')


        def abrir_dialogo_tecnicos_taller(orden):
            dropdown_tecnico = ft.Dropdown(
                options=[ft.dropdown.Option(text=tecnico['nombre'] + ' '+ tecnico['paterno'], key=tecnico['cve_empleado']) for tecnico in db_instance.tecnicos_taller(orden.cve_taller)],
                label="Agregar Técnico",
                value=None,
                width=250
            )

            def actualizar():
                contenedor_tecnicos.controls = [ft.Text(tecnico) for tecnico in orden.tecnicos]
                page.update()


            dropdown_taller = ft.Text(
                value = f'Taller: {db_instance.talleres()[orden.cve_taller]}'
            )

            contenedor_tecnicos = ft.Column(
                controls=[ft.Text(tecnico) for tecnico in orden.tecnicos],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )

            def agregar_tecnico(e):
                if dropdown_tecnico.value:
                    nuevo_tecnico = dropdown_tecnico.value
                    if orden.insertar_tecnico(cve_tecnico=nuevo_tecnico, db_instance=db_instance) == 1:
                        actualizar()
                    dropdown_tecnico.value = None
                    page.update()

            def guardar():
                cerrar_dialogo_edicion()
                connection.commit()
                refrescar_tabla()

            def cerrar():
                cerrar_dialogo_edicion()
                connection.rollback()
                orden.tecnicos = db_instance.tecnicos_orden(orden.cve_orden)

            dialogo_tecnicos_taller = ft.AlertDialog(
                title=ft.Text(f"Técnicos y Taller - Orden #{orden.cve_orden}"),
                content=ft.Column(
                    [
                        ft.Text("Técnicos asignados:", weight=ft.FontWeight.BOLD),
                        contenedor_tecnicos,
                        ft.Row([dropdown_tecnico, ft.IconButton(icon=ft.icons.ADD, on_click=agregar_tecnico)]),
                        ft.Divider(height=20, thickness=1),
                        dropdown_taller,
                    ]
                ),
                actions=[
                    ft.ElevatedButton("Guardar", on_click=lambda e: guardar()),
                    ft.ElevatedButton("Cancelar", on_click=lambda e: cerrar(), color=ft.colors.RED)
                ],
                open=True,
                on_dismiss=lambda e: cerrar()
            )

            page.overlay.append(dialogo_tecnicos_taller)
            page.update()
        
        
        def abrir_dialogo_notas(orden_preseleccionada: int | None = None):
            def cerrar(e=None):
                # no uses cerrar_dialogo_edicion() si ese cierra “todo”
                dialogo_notas.open = False
                page.update()

            # 1) combo de órdenes
            _ordenes = db_instance.ordenes()
            ordenes_dd = ft.Dropdown(
                options=[ft.dropdown.Option(text=resumir(o), key=o.cve_orden) for o in _ordenes],
                label="Seleccione una orden:",
                width=540,
            )
            if orden_preseleccionada is not None:
                ordenes_dd.value = int(orden_preseleccionada)

            # 2) listado con scroll
            contenedor = ft.Column(spacing=6, expand=True, scroll=ft.ScrollMode.AUTO)

            def item_nota(n):
                # soporta dict o tupla
                if isinstance(n, dict):
                    txt = n.get("nota") or n.get("NOTA") or n.get("descripcion") or ""
                elif isinstance(n, (list, tuple)):
                    txt = str(n[0])
                else:
                    txt = str(n or "")
                if not txt:
                    txt = "(nota vacía)"
                return ft.ListTile(title=ft.Text(txt))

            def actualizar(e=None):
                contenedor.controls.clear()
                if ordenes_dd.value:
                    try:
                        notas = db_instance.notas(int(ordenes_dd.value)) or []
                    except Exception as ex:
                        notas = []
                        print("WARN notas:", ex)
                    for n in notas:
                        contenedor.controls.append(item_nota(n))
                    if not notas:
                        contenedor.controls.append(ft.Text(
                            "No hay notas para esta orden.",
                            italic=True, size=12, color=ft.colors.GREY
                        ))
                page.update()

            ordenes_dd.on_change = actualizar

            dialogo_notas = ft.AlertDialog(
                modal=True,
                title=ft.Text("Ver notas"),
                content=ft.Column(
                    [
                        ordenes_dd,
                        ft.Container(contenedor, height=260, width=540),
                    ],
                    tight=True, width=560,
                ),
                actions=[ft.ElevatedButton("Cerrar", on_click=cerrar)],
                open=True,
            )

            page.overlay.append(dialogo_notas)
            page.update()
            actualizar()  # carga inicial

        def abrir_dialogo_nueva_nota():
            # 1) órdenes
            _ordenes = db_instance.ordenes()
            if not _ordenes:
                page.open(ft.SnackBar(ft.Text("No hay órdenes para asociar la nota.")))
                return

            campo_nota = ft.TextField(label="Nota", multiline=True, min_lines=4, expand=True)
            ordenes_dd = ft.Dropdown(
                label="Orden",
                options=[ft.dropdown.Option(text=resumir(o), key=o.cve_orden) for o in _ordenes],
                width=400,
                value=_ordenes[0].cve_orden,  # una preseleccionada
            )
            error = ft.Text("", color=ft.colors.RED)

            def cancelar(e=None):
                dialogo.open = False
                page.update()

            def guardar(e=None):
                nota_txt = (campo_nota.value or "").strip()
                ord_val = ordenes_dd.value

                if not nota_txt or ord_val in (None, ""):
                    error.value = "Rellene todos los campos"
                    page.update()
                    return

                try:
                    db_instance.insertar_nota(int(ord_val), nota_txt)
                    connection.commit()
                except Exception as ex:
                    error.value = f"Error al guardar la nota: {ex}"
                    page.update()
                    return

                dialogo.open = False
                page.open(ft.SnackBar(ft.Text("Nota agregada con éxito")))
                # abre el visor apuntando a la orden recién usada
                abrir_dialogo_notas(orden_preseleccionada=int(ord_val))
                page.update()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Nueva Nota"),
                content=ft.Column([ordenes_dd, campo_nota, error], tight=True, width=600),
                actions=[ft.ElevatedButton("Agregar", on_click=guardar),
                        ft.OutlinedButton("Cancelar", on_click=cancelar)],
                open=True,
            )
            page.overlay.append(dialogo)
            page.update()


        def abrir_dialogo_nueva_nota():
            _ordenes = db_instance.ordenes() or []
            if not _ordenes:
                page.open(ft.SnackBar(ft.Text("No hay órdenes para asociar la nota.")))
                return

            campo_nota = ft.TextField(label="Nota", multiline=True, min_lines=4, expand=True, border_color=ft.colors.BLUE_300)
            ordenes_dropdown = ft.Dropdown(
                label="Orden",
                options=[ft.dropdown.Option(text=resumir(o), key=o.cve_orden) for o in _ordenes],
                width=400,
                value=str(_ordenes[0].cve_orden),  # usa string para ser consistente
            )
            error = ft.Text("", color=ft.colors.RED)

            def cancelar(e=None):
                cerrar_dialogo_edicion()
                try: connection.rollback()
                except Exception: pass

            def guardar(e=None):
                nota_txt = (campo_nota.value or "").strip()
                ord_val = ordenes_dropdown.value
                if not nota_txt or ord_val in (None, ""):
                    error.value = "Rellene todos los campos"; page.update(); return
                try:
                    db_instance.insertar_nota(cve_orden=int(ord_val), nota=nota_txt)  # <-- forzamos int
                    connection.commit()
                except Exception as ex:
                    error.value = f"Error al guardar la nota: {ex}"; page.update(); return

                cerrar_dialogo_edicion()
                page.open(ft.SnackBar(ft.Text("Nota agregada con éxito")))
                abrir_dialogo_notas(orden_preseleccionada=int(ord_val))
                page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Nueva Nota"),
                content=ft.Column([ordenes_dropdown, campo_nota, error], tight=True, width=600),
                actions=[ft.ElevatedButton("Agregar", on_click=guardar),
                        ft.OutlinedButton("Cancelar", on_click=cancelar)],
                open=True,
                on_dismiss=lambda e: cancelar(),
            )
            
            page.overlay.append(dlg)
            page.update()
        


        def abrir_dialogo_partes():
            def guardar():
                cerrar_dialogo_edicion()
                connection.commit()
                refrescar_tabla()

            def cerrar():
                cerrar_dialogo_edicion()
                connection.rollback()

            contenedor_notas = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=300)

            def eliminar(e, nota):
                db_instance.eliminar_parte(nota['cve_orden_parte'])
                actualizar()


            def nota(nota):
                return ft.Container(ft.Row(controls=[ft.Text(str(nota['cve_orden_parte'])+'# '+(str(nota['part_no']) if nota['part_no'] is not None else '')+' $'+str(nota['precio'])+'\n'+nota['descripcion'],
                                            size=20), ft.IconButton(icon=ft.icons.DELETE_FOREVER_ROUNDED, on_click=lambda e, n=nota :eliminar(e, n),
                                                                    icon_color=ft.colors.PINK_ACCENT)],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            def actualizar():
                contenedor_notas.controls.clear()
                for n in db_instance.partes_orden(dropdown_ordenes.value):
                    contenedor_notas.controls.append(nota(n))
                page.update()

            dropdown_ordenes = ft.Dropdown(options=[ft.dropdown.Option(text=resumir(orden), key=orden.cve_orden) for orden in ordenes],
                                           on_change=lambda e: actualizar(), label='Seleccione una orden:')

            dialogo_tecnicos_taller = ft.AlertDialog(
                title=ft.Text(f"Ver partes"),
                content=ft.Column(
                    [
                        dropdown_ordenes,
                        contenedor_notas
                    ]
                ),
                actions=[
                    ft.ElevatedButton("Guardar", on_click=lambda e: guardar()),
                    ft.ElevatedButton("Cancelar", on_click=lambda e: cerrar(), color=ft.colors.RED)
                ],
                open=True,
                on_dismiss=lambda e: cerrar()
            )

            page.overlay.append(dialogo_tecnicos_taller)
            page.update()

        def abrir_dialogo_nueva_orden(db_instance):


            campo_nombre = ft.TextField(label="Nombre", expand=True)
            campo_apellido_paterno = ft.TextField(label="Apellido Paterno", expand=True)
            campo_apellido_materno = ft.TextField(label="Apellido Materno", expand=True)
            campo_correo = ft.TextField(label="Correo", expand=True)
            campo_telefono = ft.TextField(label="Teléfono", expand=True)
            campo_calle = ft.TextField(label="Calle", expand=True)
            campo_numero_calle = ft.TextField(label="Número de Calle", expand=True)
            campo_colonia = ft.TextField(label="Colonia", expand=True)
            campo_cp = ft.TextField(label="Código Postal", expand=True)
            campo_municipio = ft.TextField(label="Municipio", expand=True)
            dropdown_estado = ft.Dropdown(label="Estado", options=[], expand=True, disabled=True, on_change=lambda e: verificar())
            paises = db_instance.paises()
            dropdown_pais = ft.Dropdown(label="País", options=[ft.dropdown.Option(text=pais, key=paises[pais]) for pais in paises.keys()],
                                        expand=True, on_change= lambda e: act_estados())
            estado = ft.TextField(label='Nuevo Estado', expand=True, visible=False)
            error = ft.Text("", text_align=ft.TextAlign.CENTER, color=ft.colors.RED)

            # Placeholders amigables
            campo_correo.hint_text = "ejemplo@dominio.com"
            campo_telefono.hint_text = "10 dígitos (solo números)"

            # Validación LIVE (se ejecuta al tipear)
            def _validate_email_live(e=None):
                txt = (campo_correo.value or "").strip()
                campo_correo.error_text = None if (txt and EMAIL_RE.match(txt)) else "Correo no válido"
                page.update()

            def _validate_phone_live(e=None):
                raw = (campo_telefono.value or "").strip()
                ok = PHONE_10_RE.fullmatch(raw) or PHONE_PLUS52_RE.fullmatch(raw)
                campo_telefono.error_text = None if ok else "Use 10 dígitos o +52 y 10 dígitos"
                page.update()

            # engancha el validador
            campo_telefono.on_change = _validate_phone_live
            # (opcional) ayuda visual
            campo_telefono.hint_text = "10 dígitos o +52 y 10 dígitos"

            campo_correo.on_change = _validate_email_live
            campo_telefono.on_change = _validate_phone_live

            # (Opcional) normaliza CP a 5 dígitos al vuelo
            def _validate_cp_live(e=None):
                raw = (campo_cp.value or "")
                campo_cp.value = "".join(ch for ch in raw if ch.isdigit())[:5]
                page.update()

            campo_cp.on_change = _validate_cp_live

            # --- Número de calle ---
            HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)

            def _normalize_house(s: str) -> str:
                s = (s or "").strip().upper().replace(" ", "")
                # normalizaciones comunes
                s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
                if s in ("SN", "S-N"):
                    s = "S/N"
                return s

            def _validate_house_live(e=None):
                val = _normalize_house(campo_numero_calle.value)
                campo_numero_calle.value = val  # si no quieres auto-normalizar, comenta esta línea
                ok = bool(val and HOUSE_RE.match(val))
                campo_numero_calle.error_text = None if ok else "Use 1–6 dígitos, opcional letra (p.ej. 123B) o 'S/N'"
                page.update()

            campo_numero_calle.on_change = _validate_house_live

            def verificar():
                if dropdown_estado.value == 'Otro':
                    estado.visible=True
                else:
                    estado.visible=False
                page.update()


            def act_estados():
                estados = db_instance.estados(dropdown_pais.value)
                dropdown_estado.options = [ft.dropdown.Option(text=est, key=estados[est]) for est in estados.keys()]
                if dropdown_pais.value != '5':
                    dropdown_estado.options.insert(0, ft.dropdown.Option('Otro'))
                dropdown_estado.disabled = False
                page.update()

            campo_marca = ft.TextField(label="Marca", expand=True)
            campo_modelo = ft.TextField(label="Modelo", expand=True)
            aux = db_instance.tipos()
            campo_tipo = ft.Dropdown(label="Tipo", options=[ft.dropdown.Option(text=aux[tipo][1], key=tipo) for tipo in aux.keys()], expand=True)
            campo_nota_inicial = ft.TextField(label="Nota Inicial del Cliente", multiline=True, expand=True)

            def act_tecnicos():
                dropdown_tecnico.options = [ft.dropdown.Option(text=tecnico['nombre'] + ' ' + tecnico['paterno'], key=tecnico['cve_empleado'])
                for tecnico in db_instance.tecnicos_taller(dropdown_taller.value)]
                dropdown_tecnico.disabled = False
                page.update()

            dropdown_tecnico = dropdown_tecnico = ft.Dropdown(
                options=[],
                label="Agregar Técnico",
                value=None,
                expand=True,
                disabled=True
            )
            talleres = db_instance.talleres()
            dropdown_taller = ft.Dropdown(label="Taller", options=[ft.dropdown.Option(text=talleres[tal], key=tal) for tal in talleres.keys()],
                                          expand=True, on_change=lambda e: act_tecnicos())


            def guardar_orden(e):
                # Limpia mensajes previos de error
                error.value = ""
                campo_correo.error_text = None
                campo_telefono.error_text = None
                page.update()

                # 1) Recolecta
                nombre      = (campo_nombre.value or "").strip()
                apellido_p  = (campo_apellido_paterno.value or "").strip()
                apellido_m  = (campo_apellido_materno.value or "").strip()
                correo      = (campo_correo.value or "").strip()
                telefono_raw= (campo_telefono.value or "").strip()
                calle       = (campo_calle.value or "").strip()
                num_calle   = (campo_numero_calle.value or "").strip()
                colonia     = (campo_colonia.value or "").strip()
                municipio   = (campo_municipio.value or "").strip()
                estado_d    = dropdown_estado.value
                pais        = dropdown_pais.value
                marca       = (campo_marca.value or "").strip()
                modelo      = (campo_modelo.value or "").strip()
                tipo        = campo_tipo.value
                nota_inicial= (campo_nota_inicial.value or "").strip()
                tecnico     = dropdown_tecnico.value
                taller      = dropdown_taller.value

                # 2) Obligatorios
                if not all([
                    nombre, apellido_p, correo, telefono_raw, calle, num_calle, colonia, municipio,
                    estado_d, pais, marca, modelo, tipo, nota_inicial, tecnico, taller
                ]):
                    error.value = "Llene todos los campos obligatorios."
                    page.update()
                    return

                # 3) Código Postal: 5 dígitos
                raw_cp = (campo_cp.value or "").strip()
                cp_digits = "".join(ch for ch in raw_cp if ch.isdigit())[:5]
                if len(cp_digits) != 5:
                    error.value = "El Código Postal debe tener 5 dígitos."
                    page.update()
                    return

                # 4) Correo
                if not EMAIL_RE.match(correo):
                    campo_correo.error_text = "Correo no válido (ej. usuario@dominio.com)"
                    error.value = "Corrija los campos marcados en rojo."
                    page.update()
                    return

                # 5) Teléfono estricto: 10 dígitos o +52 y 10 dígitos → normaliza a 10
                tel_norm = normalize_mx_phone_strict(telefono_raw)
                if tel_norm is None:
                    campo_telefono.error_text = "Teléfono inválido: use 10 dígitos o +52 y 10 dígitos"
                    error.value = "Corrija los campos marcados en rojo."
                    page.update()
                    return

                # 6) Si estado = 'Otro', debe venir el texto en 'estado'
                if estado_d == 'Otro' and not (estado.value or "").strip():
                    error.value = "Llene el campo de Nuevo Estado."
                    page.update()
                    return

                # 7) Persistencia
                cli_id = None  # <- ¡siempre definimos!
                try:
                    # Crear/obtener cliente
                    if estado_d == 'Otro':
                        cli_id = db_instance.insertar_cliente_y_verificar_datos(
                            nombre, apellido_p, apellido_m, correo, tel_norm,
                            calle, num_calle, cp_digits, colonia, municipio,
                            (estado.value or "").strip(), pais
                        )
                    else:
                        cli_id = db_instance.insertar_cliente_y_verificar_datos(
                            nombre, apellido_p, apellido_m, correo, tel_norm,
                            calle, num_calle, cp_digits, colonia, municipio,
                            estado_d, pais
                        )

                    if not cli_id:
                        raise RuntimeError("No fue posible crear el cliente.")

                    # Estado inicial de la orden: En proceso (1)
                    db_instance.insertar_orden(
                        1,           # cve_status
                        marca,
                        modelo,
                        tipo,        # id de tipo (tu dropdown ya da el id)
                        nota_inicial,
                        cli_id,      # cliente creado
                        taller,
                        tecnico,
                    )

                    connection.commit()
                    page.open(ft.SnackBar(ft.Text("Orden creada con éxito")))
                    # refresca y vuelve
                    refrescar_tabla()
                    llenar_tabla_ordenes(filtro_estado.value, filtro_direccion.selected, filtro_taller.value, True)
                    page.update()
                    cancelar_orden(e)

                except Exception as ex:
                    try:
                        connection.rollback()
                    except Exception:
                        pass
                    error.value = f"Error al guardar: {ex}"
                    page.update()


            def cancelar_orden(e):
                page.title = 'Pagina principal'
                page.views.pop()
                page.go('/dashboard')

            return ft.View(
                "/nueva",
                controls=[ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Nueva Orden", size=24, weight=ft.FontWeight.BOLD),
                                error,
                                ft.Row([ft.ElevatedButton("Guardar", on_click=guardar_orden),
                                ft.ElevatedButton("Cancelar", on_click=cancelar_orden, color=ft.colors.RED)])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text("Información del Cliente", size=18, weight=ft.FontWeight.BOLD),
                        ft.Column(
                            [
                                ft.Row(
                                    [campo_nombre, campo_apellido_paterno, campo_apellido_materno]
                                ),
                                ft.Row([campo_correo, campo_telefono]),
                                ft.Row([campo_calle, campo_numero_calle,campo_cp]),
                                ft.Row([campo_colonia, campo_municipio]),
                                ft.Row([dropdown_pais, dropdown_estado, estado])
                            ],
                            spacing=5
                        ),
                        ft.Text("Información de la Orden", size=18, weight=ft.FontWeight.BOLD),
                        ft.Column(
                            [
                                ft.Row([campo_marca, campo_modelo, campo_tipo]),
                                campo_nota_inicial
                            ],
                            spacing=5
                        ),
                        ft.Text("Técnico", size=18, weight=ft.FontWeight.BOLD),
                        ft.Column(
                            [
                                ft.Row([dropdown_taller, dropdown_tecnico])
                            ],
                            spacing=5
                        ),
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.HIDDEN,
                    expand = True
                )],
                vertical_alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

        def abrir_dialogo_nueva_parte(e = None):
            def guardar():
                if ordenes_dropdown.value and piezas_dropdown.value:
                    cerrar_dialogo_edicion()
                    db_instance.parte_orden(orden=ordenes_dropdown.value, parte=piezas_dropdown.value)
                    connection.commit()
                    refrescar_tabla()
                    page.open(ft.SnackBar(ft.Text('Parte agregada con exito')))
                    page.update()
                else:
                    error.value = 'Seleccione todos los campos'
                    page.update()

            error = ft.Text('', color=ft.colors.RED)
            ordenes_dropdown = ft.Dropdown(
                options=[ft.dropdown.Option(text=resumir(orden), key=orden.cve_orden) for orden in ordenes],
                label="Seleccione la orden de la nota",
                value=None
            )

            piezas_dropdown = ft.Dropdown(
                options=[
                    ft.dropdown.Option(text=str(n['cve_parte'])+ ' '+
                                            (str(n['part_no']) if n['part_no'] is not None else '')+ ' '+ n['descripcion'] + ' $'+ str(n['precio']),
                                       key=n['cve_parte']) for n in db_instance.partes()
                ],
                label='Seleccione la pieza'
            )
            dialogo_nueva_parte = ft.AlertDialog(
                title=ft.Text('Añadir nueva parte a orden'),
                content = ft.Column(
                    [ordenes_dropdown,
                    piezas_dropdown, error],
                    height=125,
                    width=500
                ),
                actions=[
                    ft.ElevatedButton('Añadir',on_click=lambda e: guardar()),
                    ft.ElevatedButton('Cancelar', color=ft.colors.RED, on_click=lambda e: cerrar_dialogo_edicion())
                ],
                open=True,
                alignment=ft.alignment.center,
            )

            page.overlay.append(dialogo_nueva_parte)
            page.update()

        def abrir_dialogo_nuevo_servicio(e = None):
            def guardar():
                if ordenes_dropdown.value and servicios_dropdown.value:
                    cerrar_dialogo_edicion()
                    db_instance.servicio_orden(orden=ordenes_dropdown.value, servicio=servicios_dropdown.value)
                    connection.commit()
                    refrescar_tabla()
                    page.open(ft.SnackBar(ft.Text('Servicio agregado con exito')))
                    page.update()
                else:
                    error.value = 'Seleccione todos los campos'
                    page.update()

            error = ft.Text('', color=ft.colors.RED)
            ordenes_dropdown = ft.Dropdown(
                options=[ft.dropdown.Option(text=resumir(orden), key=orden.cve_orden) for orden in ordenes],
                label="Seleccione la orden de la nota",
                value=None
            )

            servicios_dropdown = ft.Dropdown(
                options=[
                    ft.dropdown.Option(text=str(n['cve_servicio'])+' $' +str(n['precio']) +' ' + n['descripcion'],
                                       key=n['cve_servicio']) for n in db_instance.servicios()
                ],
                label='Seleccione el servicio'
            )
            dialogo_nueva_parte = ft.AlertDialog(
                title=ft.Text('Añadir nuevo servicio a orden'),
                content=ft.Column(
                    [ordenes_dropdown,
                     servicios_dropdown, error],
                    height=125,
                    width=500
                ),
                actions=[
                    ft.ElevatedButton('Añadir', on_click=lambda e: guardar()),
                    ft.ElevatedButton('Cancelar', color=ft.colors.RED, on_click=lambda e: cerrar_dialogo_edicion())
                ],
                open=True,
                alignment=ft.alignment.center,
            )

            page.overlay.append(dialogo_nueva_parte)
            page.update()

        def abrir_dialogo_servicios():
            def guardar():
                cerrar_dialogo_edicion()
                connection.commit()
                refrescar_tabla()

            def cerrar():
                cerrar_dialogo_edicion()
                connection.rollback()

            contenedor_notas = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=300)

            def eliminar(e, nota):
                db_instance.eliminar_servicio(nota['cve_orden_servicio'])
                actualizar()


            def nota(nota):
                return ft.Container(ft.Row(controls=[ft.Text(str(nota['cve_orden_servicio'])+'# '+' $'+str(nota['precio'])+'\n'+nota['descripcion'],
                                            size=20), ft.IconButton(icon=ft.icons.DELETE_FOREVER_ROUNDED, on_click=lambda e, n=nota :eliminar(e, n),
                                                                    icon_color=ft.colors.PINK_ACCENT)],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            def actualizar():
                contenedor_notas.controls.clear()
                for n in db_instance.servicios_orden(dropdown_ordenes.value):
                    contenedor_notas.controls.append(nota(n))
                page.update()

            dropdown_ordenes = ft.Dropdown(options=[ft.dropdown.Option(text=resumir(orden), key=orden.cve_orden) for orden in ordenes],
                                           on_change=lambda e: actualizar(), label='Seleccione una orden:')

            dialogo_tecnicos_taller = ft.AlertDialog(
                title=ft.Text(f"Ver servicios"),
                content=ft.Column(
                    [
                        dropdown_ordenes,
                        contenedor_notas
                    ]
                ),
                actions=[
                    ft.ElevatedButton("Guardar", on_click=lambda e: guardar()),
                    ft.ElevatedButton("Cancelar", on_click=lambda e: cerrar(), color=ft.colors.RED)
                ],
                open=True,
                on_dismiss=lambda e: cerrar()
            )

            page.overlay.append(dialogo_tecnicos_taller)
            page.update()

        def abrir_dialogo_reporte(e=None):
    # dropdown se llena con lo más reciente
            ordenes_frescas = db_instance.ordenes()

            ordenes_dropdown = ft.Dropdown(
                options=[ft.dropdown.Option(text=resumir(o), key=o.cve_orden) for o in ordenes_frescas],
                label="Seleccione la orden de la nota",
                value=None,
                on_change=lambda e: crear_reporte(ordenes_dropdown.value),
            )

            def _tarifa_y_nombre_tipo(cve_tipo):
                tipos = db_instance.tipos() or {}
                try:
                    # dict: {id: (tarifa, "nombre")}
                    tarifa, nombre = tipos[cve_tipo][0], tipos[cve_tipo][1]
                except Exception:
                    t = tipos.get(cve_tipo)
                    if isinstance(t, dict):
                        tarifa = t.get("tarifa", 0)
                        nombre = t.get("descripcion", str(cve_tipo))
                    else:
                        tarifa = 0
                        nombre = str(t or cve_tipo)
                return tarifa, nombre

            def crear_reporte(ord_id):
                if not ord_id:
                    return

                # Releer la orden DESDE BD (para no usar un objeto viejo en memoria)
                try:
                    actual = next((o for o in db_instance.ordenes() if str(o.cve_orden) == str(ord_id)), None)
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"Error cargando orden: {ex}")))
                    return
                if not actual:
                    return

                tarifa, tipo_txt = _tarifa_y_nombre_tipo(actual.cve_tipo_equipo)

                piezas = db_instance.partes_orden(actual.cve_orden) or []
                servicios = db_instance.servicios_orden(actual.cve_orden) or []

                total_piezas = sum(p.get("precio", 0) for p in piezas if isinstance(p, dict))
                total_serv   = sum(s.get("precio", 0) for s in servicios if isinstance(s, dict))
                horas        = int(actual.horas or 0)
                total        = total_piezas + total_serv + (tarifa * horas)

                reporte.controls.clear()
                reporte.controls.append(
                    ft.Column(
                        [
                            ft.Text(f"Total de la orden: ${total}", size=22, weight=ft.FontWeight.BOLD),

                            ft.Row(
                                [
                                    ft.Text(f"\tTarifa {tipo_txt}:", size=18),
                                    ft.Text(f" ${tarifa}", size=18),
                                    ft.Text("Horas:", size=18, expand=True, text_align=ft.TextAlign.END),
                                    ft.Text(f" {horas}", size=18),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),

                            ft.Text(f"Total de piezas: ${total_piezas}", size=22),
                            ft.Row([ft.Text(f"\tCant. de piezas: {len(piezas)}", size=18)],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                            ft.Text(f"Total de servicios: ${total_serv}", size=22),
                            ft.Row([ft.Text(f"\tCant. de servicios: {len(servicios)}", size=18)],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.START
                    )
                )
                page.update()

            reporte = ft.Column(expand=True, alignment=ft.MainAxisAlignment.SPACE_AROUND)

            dialogo = ft.AlertDialog(
                title=ft.Text('Ver reporte por orden'),
                content=ft.Column([ordenes_dropdown, reporte], height=300, width=350),
                actions=[ft.ElevatedButton('Salir', color=ft.colors.RED, on_click=lambda e: cerrar_dialogo_edicion())],
                open=True,
                alignment=ft.alignment.center,
            )

            page.overlay.append(dialogo)
            page.update()

        usuario_info = ft.Row(

            [
                ft.Text(f"Usuario: {user.name}", weight=ft.FontWeight.BOLD),
                ft.Text(f"Rol: {user.rol}", weight=ft.FontWeight.BOLD),
                ft.Container(),
                ft.ElevatedButton("Cerrar sesión", on_click=logout, color=ft.colors.RED)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        seccion_orden = ft.Column(
             [
                ft.Text("Orden", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Obtener Reporte", on_click=lambda e: abrir_dialogo_reporte(), visible=permisos['Reporte']),
                        ft.ElevatedButton("Nueva", on_click=lambda e: nueva_orden(), visible=permisos['Nueva_Orden'])
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                )
            ]
        )


        def nueva_orden (e = None):
            page.title = "Nueva orden"
            page.views.append(abrir_dialogo_nueva_orden(db_instance))
            page.go("/nueva")
            page.update()

        orden_contenedor = ft.Container(
            content=seccion_orden,
            border_radius=5,
            padding=20,
            bgcolor=ft.colors.LIGHT_BLUE_600,
            width=300,
        )

        if not permisos['Nueva_Orden'] and not permisos['Reporte']:
            orden_contenedor.visible = False

        seccion_parte = ft.Column(
            [
                ft.Text("Parte", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nueva", on_click= lambda e: abrir_dialogo_nueva_parte(), visible=permisos['Nueva_Parte']),
                        ft.ElevatedButton("Ver/Editar", on_click= lambda e: abrir_dialogo_partes(), visible=permisos['Ver_Parte'])
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            ]
        )


        parte_contenedor = ft.Container(
            content=seccion_parte,
            border_radius=5,
            padding=20,
            bgcolor=ft.colors.LIGHT_BLUE_600,
            width=300
        )
        if not permisos['Nueva_Parte'] and not permisos['Ver_Parte']:
            parte_contenedor.visible = False


        seccion_servicio = ft.Column(
            [
                ft.Text("Servicio", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nuevo", on_click=lambda e: abrir_dialogo_nuevo_servicio(), visible=permisos['Nuevo_Servicio']),
                        ft.ElevatedButton("Ver/Editar", on_click= lambda e: abrir_dialogo_servicios(), visible=permisos['Ver_Servicio'])
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND
                )
            ]
        )



        servicio_contenedor = ft.Container(
            content=seccion_servicio,
            border_radius=5,
            padding=20,
            bgcolor=ft.colors.LIGHT_BLUE_600,
            width=300
        )
        if not permisos['Nuevo_Servicio'] and not permisos['Ver_Servicio']:
            servicio_contenedor.visible = False

        return ft.View(
            "/dashboard",
            controls=[
                usuario_info,
                ft.Divider(),
                ft.Row([orden_contenedor, parte_contenedor, servicio_contenedor, nota_contenedor],
                       alignment=ft.MainAxisAlignment.SPACE_AROUND),
                ft.Divider(height=20, thickness=1),
                filtros,
                encabezado_tabla,
                contenedor_ordenes
            ],
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


    page.views.append(create_login_view())
    page.overlay.append(dialogo_conexiones)
    page.overlay.append(dialogo_acerca_de)

    # FAB también a nivel de Page
    page.floating_action_button = make_login_chatbot_fab(page)
    page.update()

    page.go("/")


