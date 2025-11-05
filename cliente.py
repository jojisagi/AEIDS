# view/cliente.py
from __future__ import annotations
import flet as ft

# Compat Flet
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons


# -------- utilidades suaves --------
def _get(obj, keys, default=""):
    """
    Obtiene atributo/campo usando varias claves:
    - dict: prioriza claves exactas
    - objeto: prioriza atributos
    """
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            v = obj.get(k)
            return "" if v is None else v
        if hasattr(obj, k):
            v = getattr(obj, k)
            return "" if v is None else v
    return default


def _call_first_if_present(target, names: list[str], *args, **kwargs):
    """
    Busca el primer método en 'names' que exista en target y lo llama.
    Devuelve (ok:bool, retorno:any|None, nombre_usado:str|None)
    """
    for n in names:
        if hasattr(target, n):
            try:
                return True, getattr(target, n)(*args, **kwargs), n
            except TypeError:
                # Reintenta pasando todo como kwargs "amplios" si el método admite **kwargs
                try:
                    return True, getattr(target, n)(**kwargs), n
                except Exception:
                    pass
            except Exception:
                pass
    return False, None, None


# -------------------------------------------------
# Diálogo: editar cliente (como en tu simple_view.py)
# -------------------------------------------------
def open_editar_cliente_dialog(
    page: ft.Page,
    db_instance,
    cliente_obj,           # dict/obj del cliente actual
    cve_orden: int | str,  # se muestra en el título, por contexto
    on_saved=None,
):
    # Campos existentes del cliente (tolerantes a nombres)
    tf_nombre  = ft.TextField(label="Nombre",      value=_get(cliente_obj, ["nombre", "nom", "name"]))
    tf_pat     = ft.TextField(label="Apellido paterno", value=_get(cliente_obj, ["paterno", "ap_paterno", "apellido_paterno"]))
    tf_mat     = ft.TextField(label="Apellido materno", value=_get(cliente_obj, ["materno", "ap_materno", "apellido_materno"]))
    tf_correo  = ft.TextField(label="Correo",      value=_get(cliente_obj, ["correo", "email", "mail"]))
    tf_tel     = ft.TextField(label="Telefono",    value=_get(cliente_obj, ["telefono", "tel", "phone"]))
    tf_calle   = ft.TextField(label="Calle",       value=_get(cliente_obj, ["dir_calle", "calle"]))
    tf_numero  = ft.TextField(label="No. Calle",   value=_get(cliente_obj, ["dir_numero", "numero", "num_ext"]))

    error = ft.Text("", color=ft.colors.RED_300)

    def cerrar(_=None):
        page.dialog.open = False
        page.update()

    def guardar(_=None):
        # Colecta valores
        nombre   = (tf_nombre.value or "").strip()
        paterno  = (tf_pat.value or "").strip()
        materno  = (tf_mat.value or "").strip()
        correo   = (tf_correo.value or "").strip()
        telefono = (tf_tel.value or "").strip()
        calle    = (tf_calle.value or "").strip()
        numero   = (tf_numero.value or "").strip()

        if not nombre or not paterno or not correo:
            error.value = "Nombre, Ap. Paterno y Correo son obligatorios."
            page.update()
            return

        # Buscamos un método de actualización en la fachada
        # Ajusta/añade el que uses realmente si no se detecta
        CANDIDATE_METHODS = [
            "actualizar_cliente",
            "update_cliente",
            "editar_cliente",
            "cliente_update",
            "cliente_actualizar",
            "update",
        ]

        payload = dict(
            nombre=nombre,
            paterno=paterno,
            materno=materno,
            correo=correo,
            telefono=telefono,
            calle=calle,
            numero=numero,
            # permite id si tu método lo requiere
            cve_cliente=_get(cliente_obj, ["cve_cliente", "id", "cliente"]),
        )

        ok, res, used = _call_first_if_present(db_instance, CANDIDATE_METHODS, **payload)
        if not ok:
            # Algunos proyectos exponen el controlador/DAO bajo db_instance._cliente
            if hasattr(db_instance, "_cliente"):
                ok, res, used = _call_first_if_present(getattr(db_instance, "_cliente"), CANDIDATE_METHODS, **payload)

        if ok:
            try:
                if hasattr(db_instance, "get_connection"):
                    conn = db_instance.get_connection()
                    if conn:
                        conn.commit()
            except Exception:
                pass

            page.open(ft.SnackBar(ft.Text("Cliente actualizado")))
            cerrar()
            if callable(on_saved):
                try:
                    on_saved()
                except Exception:
                    pass
        else:
            error.value = "No se encontró método para actualizar el cliente en la fachada."
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Editar Cliente Orden #{cve_orden}"),
        content=ft.Column(
            controls=[
                tf_nombre, tf_pat, tf_mat, tf_correo, tf_tel, tf_calle, tf_numero,
                ft.Container(height=4),
                error,
            ],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        actions=[
            ft.TextButton("Guardar", on_click=guardar),
            ft.TextButton("Cancelar", on_click=cerrar),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=18),
    )

    page.dialog = dlg
    dlg.open = True
    page.update()