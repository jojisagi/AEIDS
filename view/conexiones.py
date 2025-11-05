# view/conexiones.py
import flet as ft
from utils.config import cargar_datos_conexion, guardar_datos_conexion

def open_conexiones_dialog(page: ft.Page, state) -> None:
    datos = cargar_datos_conexion("conexion_db.txt")

    host = ft.TextField(label="Host", width=300, value=datos["hostname"])
    port = ft.TextField(label="Puerto", width=300, value=datos["port"])
    svc  = ft.TextField(label="Servicio", width=300, value=datos["service_name"])
    mongo= ft.TextField(label="MongoDB", width=300, multiline=True, value=datos["mongodb_url"])
    api  = ft.TextField(label="OpenAI API Key", password=True, can_reveal_password=True,
                        width=300, value=page.client_storage.get("openai_api_key") or "")

    msg = ft.Text("", color="red")

    def guardar(e=None):
        ok = all([(host.value or "").strip(), (port.value or "").strip(), (svc.value or "").strip(), (mongo.value or "").strip()])
        if ok:
            guardar_datos_conexion("conexion_db.txt",
                                   hostname=host.value.strip(),
                                   port=port.value.strip(),
                                   service_name=svc.value.strip(),
                                   mongodb_url=mongo.value.strip())
            state.datos = cargar_datos_conexion("conexion_db.txt")

        # API Key local
        key = (api.value or "").strip()
        try:
            if key: page.client_storage.set("openai_api_key", key)
            else:   page.client_storage.remove("openai_api_key")
        except Exception as ex:
            print("WARN client_storage", ex)

        msg.value = "Información guardada" if ok else "Complete todos los campos"
        msg.color = "green" if ok else "red"
        page.update()

    def cerrar(e=None):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Configuración de Conexiones"),
        content=ft.Column([host, port, svc, mongo, api, msg], tight=True, width=360),
        actions=[ft.ElevatedButton("Guardar", on_click=guardar), ft.TextButton("Salir", on_click=cerrar)],
        open=True
    )
    page.overlay.append(dlg)
    page.update()