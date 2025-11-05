# view/cliente.py
from __future__ import annotations
import flet as ft

# Compat Flet
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons


# ---------------- utilidades ----------------
def _from_sources(sources, keys, default: str = "") -> str:
    """
    Busca un valor en una o varias fuentes (dict/obj) usando una lista de claves posibles.
    Devuelve siempre str (o default).
    """
    srcs = sources if isinstance(sources, (list, tuple)) else [sources]
    for src in srcs:
        if src is None:
            continue
        for k in keys:
            if isinstance(src, dict) and k in src:
                v = src.get(k)
                return "" if v is None else str(v)
            if hasattr(src, k):
                v = getattr(src, k)
                return "" if v is None else str(v)
    return default


def _kv(label: str, value: str) -> ft.Control:
    return ft.Row(
        [ft.Text(label, weight=ft.FontWeight.BOLD, width=140), ft.Text(value or "—")],
        alignment=ft.MainAxisAlignment.START,
    )


# ---------------- diálogo principal ----------------
def open_editar_cliente_dialog(
    page: ft.Page,
    db_instance,
    cliente_obj,            # dict/obj opcional que venga de la UI (puede ser None)
    cve_orden: int | str,   # id de la orden para cargar el cliente real
    on_saved=None,
):
    """
    - Carga el cliente vinculado a la orden (si existe) usando DBFacade.cliente_id_por_orden + cliente_detalle.
    - Muestra una sección 'Actual (solo lectura)' con los valores vigentes.
    - Precarga los TextField con esos valores para facilitar la edición.
    - Guarda con DBFacade.guardar_cliente_de_orden (upsert y re-vinculación).
    """

    # ---------- 1) Cargar detalle real desde la BD (si hay cliente ligado) ----------
    detalle_db: dict = {}
    try:
        cli_id = db_instance.cliente_id_por_orden(int(cve_orden))
        if cli_id:
            # usa el helper de la fachada que lee directo de la tabla cliente
            detalle_db = db_instance.cliente_detalle(int(cli_id)) or {}
    except Exception:
        detalle_db = {}

    # Fuentes en prioridad: lo que ya trae la UI, luego lo que venga de BD
    fuentes = [cliente_obj, detalle_db]

    # ---------- 2) Normalizar valores actuales ----------
    curr_nombre   = _from_sources(fuentes, ["nombre", "name", "nom"])
    curr_paterno  = _from_sources(fuentes, ["paterno", "ap_paterno", "apellido_paterno"])
    curr_materno  = _from_sources(fuentes, ["materno", "ap_materno", "apellido_materno"])
    curr_correo   = _from_sources(fuentes, ["correo", "email", "mail"])
    curr_tel      = _from_sources(fuentes, ["telefono", "tel", "phone"])
    curr_calle    = _from_sources(fuentes, ["calle", "dir_calle"])
    # Nota: si en tu esquema no existe num_calle, simplemente quedará vacío (no lo usamos para guardar)
    curr_num      = _from_sources(fuentes, ["num_calle", "dir_numero", "numero", "num_ext"])

    # ---------- 3) Campos editables (precargados) ----------
    tf_nombre  = ft.TextField(label="Nombre",           value=curr_nombre)
    tf_pat     = ft.TextField(label="Apellido paterno", value=curr_paterno)
    tf_mat     = ft.TextField(label="Apellido materno", value=curr_materno)
    tf_correo  = ft.TextField(label="Correo",           value=curr_correo)
    tf_tel     = ft.TextField(label="Teléfono",         value=curr_tel)
    tf_calle   = ft.TextField(label="Calle",            value=curr_calle)
    tf_num     = ft.TextField(label="No. Calle",        value=curr_num)

    # Forzamos una asignación posterior por si el framework no respeta el 'value' inicial en algunos entornos.
    def _apply_prefill():
        tf_nombre.value = curr_nombre
        tf_pat.value    = curr_paterno
        tf_mat.value    = curr_materno
        tf_correo.value = curr_correo
        tf_tel.value    = curr_tel
        tf_calle.value  = curr_calle
        tf_num.value    = curr_num

    # ---------- 4) Vista readonly (valores actuales) ----------
    readonly_box = ft.Container(
        bgcolor=ft.colors.with_opacity(0.05, ft.colors.ON_SURFACE),
        padding=12,
        border_radius=12,
        content=ft.Column(
            [
                ft.Text("Actual (solo lectura)", weight=ft.FontWeight.BOLD),
                _kv("Nombre:", curr_nombre),
                _kv("Ap. paterno:", curr_paterno),
                _kv("Ap. materno:", curr_materno),
                _kv("Correo:", curr_correo),
                _kv("Teléfono:", curr_tel),
                _kv("Calle:", curr_calle),
                _kv("No. Calle:", curr_num),
            ],
            tight=True,
            spacing=6,
        ),
    )

    error_lbl = ft.Text("", color=ft.colors.RED_300)
    dlg = ft.AlertDialog(modal=True)

    def cerrar(_=None):
        dlg.open = False
        page.update()

    def guardar(_=None):
        error_lbl.value = ""
        page.update()

        nombre   = (tf_nombre.value or "").strip()
        paterno  = (tf_pat.value or "").strip()
        materno  = (tf_mat.value or "").strip()
        correo   = (tf_correo.value or "").strip()
        telefono = (tf_tel.value or "").strip()
        calle    = (tf_calle.value or "").strip()
        num_calle= (tf_num.value or "").strip()

        if not nombre or not paterno:
            error_lbl.value = "Nombre y Apellido paterno son obligatorios."
            page.update()
            return

        try:
            # Upsert del cliente y re-vinculación a la orden (usa la fachada)
            db_instance.guardar_cliente_de_orden(
                int(cve_orden),
                nombre=nombre,
                paterno=paterno,
                materno=materno,
                correo=correo,
                telefono=telefono,
                calle=calle,
                num_calle=num_calle,
                # cp5/colonia/municipio/estado/pais son opcionales; omitir si no los manejas aquí
            )

            # Commit best-effort
            try:
                conn = db_instance.get_connection()
                if conn:
                    conn.commit()
            except Exception:
                pass

            page.open(ft.SnackBar(ft.Text(f"Cliente de la orden #{cve_orden} actualizado")))
            cerrar()
            if callable(on_saved):
                try:
                    on_saved()
                except Exception:
                    pass

        except Exception as ex:
            try:
                conn = db_instance.get_connection()
                if conn:
                    conn.rollback()
            except Exception:
                pass
            error_lbl.value = f"Error al guardar: {ex}"
            page.update()

    dlg.title = ft.Text(f"Editar Cliente Orden #{cve_orden}", weight=ft.FontWeight.BOLD)
    dlg.content = ft.Column(
        controls=[
            error_lbl,
            readonly_box,
            ft.Divider(opacity=0.1),
            ft.Text("Nuevo / editar", weight=ft.FontWeight.BOLD),
            tf_nombre, tf_pat, tf_mat, tf_correo, tf_tel, tf_calle, tf_num,
        ],
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )
    dlg.actions = [
        ft.FilledButton("Guardar", icon=ft.icons.SAVE, on_click=guardar),
        ft.TextButton("Cancelar", on_click=cerrar),
    ]
    dlg.actions_alignment = ft.MainAxisAlignment.END
    dlg.shape = ft.RoundedRectangleBorder(radius=18)

    page.dialog = dlg
    dlg.open = True

    # Aplicamos el prefill por si el constructor no lo mostró.
    _apply_prefill()
    page.update()


# Alias por compatibilidad con otros imports
open_editar_cliente_de_orden_dialog = open_editar_cliente_dialog