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
    if obj is None:
        return default
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


def _fetch_cliente_detalle_resistente(db_instance, cve_orden: int):
    """
    Intenta obtener el cve_cliente y luego el detalle para precargar.
    Devuelve {} si no se pudo.
    """
    try:
        cve_cli = db_instance.cliente_id_por_orden(int(cve_orden))
    except Exception:
        cve_cli = None

    if not cve_cli:
        return {}

    # Camino 1: método de la fachada
    try:
        data = db_instance.cliente_detalle(int(cve_cli)) or {}
        if isinstance(data, dict) and any((str(v).strip() for v in data.values() if v is not None)):
            return data
    except Exception:
        pass

    # Camino 2: si expone un controlador interno
    try:
        if hasattr(db_instance, "_cliente") and hasattr(db_instance._cliente, "detalle"):
            data = db_instance._cliente.detalle(int(cve_cli)) or {}
            if isinstance(data, dict) and any((str(v).strip() for v in data.values() if v is not None)):
                return data
    except Exception:
        pass

    # Si nada funcionó:
    return {}


# -------------------------------------------------
# Diálogo: editar cliente (precarga con fallback)
# -------------------------------------------------
def open_editar_cliente_dialog(
    page: ft.Page,
    db_instance,
    cliente_obj,           # puede venir dict, objeto o incluso None
    cve_orden: int | str,  # se usa para autoconseguir el cliente si falta
    on_saved=None,
):
    # --- asegurar datos precargados ---
    cve_orden_int = int(str(cve_orden))
    if not (isinstance(cliente_obj, dict) and any((str(v).strip() for v in cliente_obj.values() if v is not None))):
        # si llega vacío, buscar directamente en DB con la orden
        cliente_obj = _fetch_cliente_detalle_resistente(db_instance, cve_orden_int)

    # Campos existentes del cliente (tolerantes a nombres)
    tf_nombre  = ft.TextField(label="Nombre",             value=_get(cliente_obj, ["nombre", "nom", "name"]))
    tf_pat     = ft.TextField(label="Apellido paterno",   value=_get(cliente_obj, ["paterno", "ap_paterno", "apellido_paterno"]))
    tf_mat     = ft.TextField(label="Apellido materno",   value=_get(cliente_obj, ["materno", "ap_materno", "apellido_materno"]))
    tf_correo  = ft.TextField(label="Correo",             value=_get(cliente_obj, ["correo", "email", "mail"]))
    tf_tel     = ft.TextField(label="Teléfono",           value=_get(cliente_obj, ["telefono", "tel", "phone"]))
    tf_calle   = ft.TextField(label="Calle",              value=_get(cliente_obj, ["calle", "dir_calle", "direccion", "domicilio", "direccion1"]))
    tf_numero  = ft.TextField(label="No. Calle",          value=_get(cliente_obj, ["num_calle", "no_calle", "numero", "num_ext", "numero_calle"]))

    # Mensaje pequeño para depuración (opcional: comenta si no lo quieres)
    info_precarga = ft.Text(
        value="(precargado)" if any([tf_nombre.value, tf_pat.value, tf_correo.value]) else "(sin datos del cliente)",
        color=ft.colors.GREY,
        size=11,
        italic=True,
    )

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

        # 1) Intentar una actualización directa (si existe en la fachada)
        ok, _res, used = _call_first_if_present(
            db_instance,
            ["actualizar_cliente", "update_cliente", "editar_cliente", "cliente_update", "cliente_actualizar", "update"],
            cve_cliente=_get(cliente_obj, ["cve_cliente", "id", "cliente"]),
            nombre=nombre, paterno=paterno, materno=materno,
            correo=correo, telefono=telefono,
            calle=calle, num_calle=numero,
        )

        # 2) Si no hay método directo, usa el helper de la fachada que sabe vincular por orden
        if not ok:
            try:
                db_instance.guardar_cliente_de_orden(
                    cve_orden_int,
                    nombre=nombre, paterno=paterno, materno=materno,
                    correo=correo, telefono=telefono,
                    calle=calle, num_calle=numero
                )
                ok = True
            except Exception:
                ok = False

        if ok:
            # commit suave
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
            error.value = "No se pudo actualizar el cliente (verifica la fachada/controlador)."
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Editar Cliente – Orden #{cve_orden}"),
        content=ft.Column(
            controls=[
                info_precarga,
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