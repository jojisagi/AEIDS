# view/dashboard.py
from __future__ import annotations
import re
import flet as ft

# Compat Flet (algunas versiones exponen Colors/Icons con mayúscula)
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

from .chat_fab import make_chat_fab
# Estos imports quedan, pero más abajo sobrescribimos con funciones locales
from .notas import open_notas_dialog, open_nueva_nota_dialog
from .partes import open_partes_dialog, open_nueva_parte_dialog
from .servicios import open_servicios_dialog, open_nuevo_servicio_dialog
from .reporte import open_reporte_dialog
from .nueva_orden import build_new_order_view
from .charts import open_status_chart_dialog  # ← NUEVO

# --- Validaciones ligeras usadas en los formularios ---
EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
PHONE_10_RE = re.compile(r"^\d{10}$")
PHONE_PLUS52_RE = re.compile(r"^\+52\d{10}$")
HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)


def _normalize_house(s: str) -> str:
    s = (s or "").strip().upper().replace(" ", "")
    s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
    if s in ("SN", "S-N"):
        s = "S/N"
    return s


def normalize_mx_phone_strict(raw: str) -> str | None:
    s = (raw or "").strip()
    if PHONE_10_RE.fullmatch(s):
        return s
    if PHONE_PLUS52_RE.fullmatch(s):
        return s[-10:]
    return None


def build_dashboard_view(page: ft.Page, db_instance, connection, user) -> ft.View:
    # === FAB del Chat ===
    page.floating_action_button = make_chat_fab(page)

    # ===== Helpers generales =====
    def _normalize_status_name(name: str) -> str:
        s = (name or "").strip().lower()
        if s in ("en proceso", "en proceso."):
            return "En proceso"
        if s in ("terminada", "terminado"):
            return "Terminado"
        if s in ("recogida", "recogido"):
            return "Recogido"
        return (name or "").strip()

    def _status_catalog_from_db() -> dict[int, str]:
        """Devuelve {id:int -> nombre:str}, tolerante a dict/tupla/lista."""
        try:
            filas = db_instance.statuses()
        except Exception:
            filas = None

        cat: dict[int, str] = {}
        if isinstance(filas, dict):
            for k, v in filas.items():
                try:
                    cat[int(str(k).strip())] = str(v or "").strip()
                except Exception:
                    pass
            if cat:
                return cat

        for it in (filas or []):
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

        return cat or {1: "En proceso", 2: "Terminado", 3: "Recogido"}

    def _tipos_catalogo() -> dict:
        """Devuelve dict id->nombre (acepta múltiples formatos)."""
        raw = db_instance.tipos() or {}
        if isinstance(raw, dict):
            out = {}
            for k, v in raw.items():
                if isinstance(v, (list, tuple)):
                    out[k] = str(v[1] if len(v) > 1 else v[0])
                elif isinstance(v, dict):
                    out[k] = v.get("nombre") or v.get("descripcion") or str(v)
                else:
                    out[k] = str(v)
            return out
        out = {}
        for it in raw:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                out[it[0]] = str(it[1])
            elif isinstance(it, dict):
                _id = it.get("id") or it.get("cve_tipo_equipo")
                _nm = it.get("nombre") or it.get("descripcion")
                if _id is not None and _nm is not None:
                    out[_id] = str(_nm)
        return out

    status_cat = _status_catalog_from_db()  # cache inicial

    def _status_chip(nombre_ui: str):
        color = {
            "En proceso": ft.colors.DEEP_PURPLE,
            "Terminado": ft.colors.GREEN,
            "Recogido": ft.colors.AMBER_900,
            "Alta": ft.colors.LIGHT_BLUE_200,
        }.get(nombre_ui, ft.colors.AMBER)
        return ft.Container(
            content=ft.Text(nombre_ui, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            border_radius=10,
            bgcolor=color,
            width=100,
            alignment=ft.alignment.center,
            height=30,
        )

    def _ui_status_name(name_or_id):
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
        if raw in ("Alta", "En proceso", "Terminado", "Recogido"):
            return raw
        return mapping.get(s, "En proceso")

    def _status_id_from_ui(value_from_ui) -> int | None:
        """Acepta '2'|'Terminado'|2 y devuelve id usando catálogo real."""
        if isinstance(value_from_ui, int):
            return value_from_ui
        s = ("" if value_from_ui is None else str(value_from_ui)).strip()
        if s.isdigit():
            return int(s)
        inv = {(v or "").strip().lower(): k for k, v in status_cat.items()}
        s_low = s.lower()
        if s_low == "terminado":
            s_low = "terminado" if "terminado" in inv else "terminada"
        if s_low == "recogido":
            s_low = "recogido" if "recogido" in inv else "recogida"
        return inv.get(s_low)

    def _tipo_id_from_ui(value_or_label) -> int | None:
        """Convierte id o etiqueta de tipo a id real."""
        if isinstance(value_or_label, int):
            return value_or_label
        s = ("" if value_or_label is None else str(value_or_label)).strip()
        if s.isdigit():
            return int(s)
        tipos = _tipos_catalogo()
        inv = {(v or "").strip().lower(): k for k, v in tipos.items()}
        return inv.get(s.lower())

    # ===== Encabezado y sesión =====
    def logout(e):
        page.title = "Inicio de Sesión"
        try:
            db_instance.close_connection()
        except Exception:
            pass
        page.views.pop()
        page.go("/")

    usuario_info = ft.Row(
        [
            ft.Text(f"Usuario: {user.name}", weight=ft.FontWeight.BOLD),
            ft.Text(f"Rol: {user.rol}", weight=ft.FontWeight.BOLD),
            ft.Container(),
            ft.ElevatedButton("Cerrar sesión", on_click=logout, color=ft.colors.RED),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # ===== filtros =====
    _seen = set()
    ui_statuses = []
    for raw in status_cat.values():
        n = _normalize_status_name(raw)
        if n not in _seen:
            _seen.add(n)
            ui_statuses.append(n)

    filtro_estado = ft.Dropdown(
        options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(s) for s in ui_statuses],
        value="Todos",
        label="Filtrar ordenes por Status",
    )

    talleres_raw = db_instance.talleres() or {}
    if isinstance(talleres_raw, dict):
        taller_opts = [("0", "Todos")] + [(str(k), str(v)) for k, v in talleres_raw.items()]
    else:
        taller_opts = [("0", "Todos")]
        for it in talleres_raw:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                taller_opts.append((str(it[0]), str(it[1])))

    filtro_taller = ft.Dropdown(
        label="Filtrar ordenes por Taller",
        options=[ft.dropdown.Option(text=txt, key=key) for key, txt in taller_opts],
        value="0",
    )

    def toggle_dir(e):
        btn_dir.selected = not btn_dir.selected
        btn_dir.update()
        llenar_tabla(True)

    btn_dir = ft.IconButton(
        icon=ft.icons.ARROW_DOWNWARD,
        selected_icon=ft.icons.ARROW_UPWARD,
        on_click=toggle_dir,
        selected=False,
        tooltip="Invertir orden",
    )

    # Botón Gráfica junto a la flecha
    btn_chart = ft.ElevatedButton(
        "Gráfica",
        on_click=lambda e: open_status_chart_dialog(page, db_instance, _ui_status_name),
        tooltip="Ver resumen por estatus",
    )

    filtros = ft.Row([filtro_estado, filtro_taller, btn_dir, btn_chart], spacing=12)

    # ===== utilidades de diálogo (compat Flet) =====
    def _open_dialog(dlg: ft.AlertDialog):
        try:
            page.open(dlg)
        except Exception:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def _close_dialog(dlg: ft.AlertDialog | None = None):
        try:
            page.close(dlg if dlg else page.dialog)
        except Exception:
            if dlg is not None:
                dlg.open = False
            elif page.dialog:
                page.dialog.open = False
            page.update()

    # ===== Persistencia: UPDATEs reales =====
    def _update_orden_base(orden_id: int, marca: str, tipo_id: int, modelo: str, status_id: int):
        cur = connection.cursor()
        cur.execute(
            """
            UPDATE orden
               SET eq_marca        = :marca,
                   cve_tipo_equipo = :tipo_id,
                   eq_modelo       = :modelo,
                   cve_status      = :status_id
             WHERE cve_orden       = :ord
            """,
            dict(marca=marca, tipo_id=int(tipo_id), modelo=modelo, status_id=int(status_id), ord=int(orden_id)),
        )

    def _actualizar_horas_orden(cve_orden: int, horas: int):
        cur = connection.cursor()
        cur.execute(
            """
            UPDATE orden_tecnicos ot
               SET ot.horas = :horas
             WHERE ot.cve_orden = :ord
               AND ot.cve_empleado = (
                     SELECT cve_empleado FROM orden_tecnicos
                      WHERE cve_orden = :ord
                      FETCH FIRST 1 ROWS ONLY
               )
            """,
            dict(horas=int(horas), ord=int(cve_orden)),
        )

    # ===== Diálogos de técnicos/taller, cliente y orden =====
    def open_tecnicos_taller_dialog(o):
        try:
            tecnicos = db_instance.tecnicos_orden(getattr(o, "cve_orden", None), horas=True) or []
        except Exception:
            tecnicos = []
        if not tecnicos:
            try:
                tecnicos = db_instance.tecnicos_taller(getattr(o, "cve_taller", None)) or []
            except Exception:
                tecnicos = []

        rows = []
        if tecnicos:
            for t in tecnicos:
                nombre = " ".join(str(t.get(k, "")).strip() for k in ("nombre", "paterno") if t.get(k))
                horas = str(t.get("horas", "")) if isinstance(t, dict) else ""
                rows.append(
                    ft.Row(
                        [ft.Text(nombre), ft.Container(expand=True), ft.Text(("Horas: " + horas) if horas else "")],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
        else:
            rows = [ft.Text("Sin técnicos registrados para esta orden/taller.")]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Técnicos / Taller — Orden #{getattr(o, 'cve_orden', '')}"),
            content=ft.Container(width=520, content=ft.Column(rows, tight=True, height=260, scroll=ft.ScrollMode.AUTO)),
            actions=[ft.ElevatedButton("Cerrar", on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        _open_dialog(dlg)

    def open_edit_client_dialog(o):
        """Intenta resolver un objeto cliente con .guardar(...). Si no es posible, avisa."""
        cliente_obj = getattr(o, "cliente_obj", None)
        if cliente_obj is None:
            maybe = getattr(o, "cliente", None)
            if not isinstance(maybe, str):
                cliente_obj = maybe

        if cliente_obj is None:
            for meth in ("cliente_por_orden", "cliente_de_orden", "get_cliente_por_orden"):
                if hasattr(db_instance, meth):
                    try:
                        cliente_obj = getattr(db_instance, meth)(int(o.cve_orden))
                        if cliente_obj:
                            break
                    except Exception:
                        pass

        nombre = ft.TextField(label="Nombre", expand=True, width=300, value=getattr(cliente_obj, "nombre", "") or "")
        paterno = ft.TextField(label="Apellido paterno", expand=True, width=300, value=getattr(cliente_obj, "paterno", "") or "")
        materno = ft.TextField(label="Apellido materno", expand=True, width=300, value=getattr(cliente_obj, "materno", "") or "")
        correo = ft.TextField(label="Correo", expand=True, width=300, value=getattr(cliente_obj, "correo", "") or "")
        telefono = ft.TextField(label="Teléfono", expand=True, width=300, value=getattr(cliente_obj, "telefono", "") or "")
        calle = ft.TextField(label="Calle", expand=True, width=300, value=getattr(cliente_obj, "dir_calle", "") or "")
        num = ft.TextField(label="No. Calle", expand=True, width=300, value=getattr(cliente_obj, "dir_num", "") or "")
        err = ft.Text("", color=ft.colors.RED)

        def _val_email_live(e=None):
            txt = (correo.value or "").strip()
            correo.error_text = None if (txt and EMAIL_RE.match(txt)) else "Correo no válido"
            page.update()

        def _val_phone_live(e=None):
            raw = (telefono.value or "").strip()
            ok = PHONE_10_RE.fullmatch(raw) or PHONE_PLUS52_RE.fullmatch(raw)
            telefono.error_text = None if ok else "Use 10 dígitos o +52 y 10 dígitos"
            page.update()

        def _val_house_live(e=None):
            val = _normalize_house(num.value)
            num.value = val
            ok = bool(val and HOUSE_RE.match(val))
            num.error_text = None if ok else "Use 1–6 dígitos, opcional letra o 'S/N'"
            page.update()

        correo.on_change = _val_email_live
        telefono.on_change = _val_phone_live
        num.on_change = _val_house_live

        def guardar(e=None):
            if not (nombre.value and paterno.value and correo.value and telefono.value and calle.value and num.value):
                err.value = "Llene todos los campos obligatorios."
                page.update()
                return
            if not EMAIL_RE.match(correo.value.strip()):
                correo.error_text = "Correo no válido"
                err.value = "Corrija los campos marcados."
                page.update()
                return
            tel = normalize_mx_phone_strict(telefono.value)
            if tel is None:
                telefono.error_text = "Teléfono inválido"
                err.value = "Corrija los campos marcados."
                page.update()
                return
            num_norm = _normalize_house(num.value)
            if not HOUSE_RE.match(num_norm):
                num.error_text = "Número inválido"
                err.value = "Corrija los campos marcados."
                page.update()
                return

            try:
                if cliente_obj and hasattr(cliente_obj, "guardar"):
                    cliente_obj.guardar(
                        db_instance,
                        (nombre.value or "").strip(),
                        (paterno.value or "").strip(),
                        (materno.value or "").strip(),
                        (correo.value or "").strip(),
                        tel,
                        (calle.value or "").strip(),
                        num_norm,
                    )
                else:
                    if hasattr(db_instance, "guardar_cliente_de_orden"):
                        db_instance.guardar_cliente_de_orden(
                            int(o.cve_orden),
                            (nombre.value or "").strip(),
                            (paterno.value or "").strip(),
                            (materno.value or "").strip(),
                            (correo.value or "").strip(),
                            tel,
                            (calle.value or "").strip(),
                            num_norm,
                        )
                    else:
                        page.open(ft.SnackBar(ft.Text("No hay método para guardar cliente (agrega repo.guardar_cliente_de_orden).")))
                        return

                try:
                    connection.commit()
                except Exception:
                    pass
                _close_dialog(dlg)
                page.open(ft.SnackBar(ft.Text("Cliente actualizado con éxito")))
                llenar_tabla(True)
            except Exception as ex:
                try:
                    connection.rollback()
                except Exception:
                    pass
                err.value = f"Error al guardar: {ex}"
                page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar Cliente Orden #{getattr(o, 'cve_orden', '')}"),
            content=ft.Container(
                width=520,
                content=ft.Column([nombre, paterno, materno, correo, telefono, calle, num, err], tight=True, height=360, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[ft.ElevatedButton("Guardar", on_click=guardar), ft.OutlinedButton("Cancelar", on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        _open_dialog(dlg)

    def open_edit_order_dialog(o):
        tipos_cat = _tipos_catalogo()  # id->nombre
        tf_marca = ft.TextField(label="Marca", value=str(getattr(o, "eq_marca", "") or ""))
        tf_modelo = ft.TextField(label="Modelo", value=str(getattr(o, "eq_modelo", "") or ""))

        dd_tipo = ft.Dropdown(
            label="Tipo",
            options=[ft.dropdown.Option(text=v, key=str(k)) for k, v in tipos_cat.items()],
            value=str(getattr(o, "cve_tipo_equipo", "")) if str(getattr(o, "cve_tipo_equipo", "")) in {str(k) for k in tipos_cat.keys()} else None,
        )

        current_status_ui = _ui_status_name(getattr(o, "cve_status", None))
        rg_status = ft.RadioGroup(
            content=ft.Column(
                [
                    ft.Radio(value="En proceso", label="En proceso"),
                    ft.Radio(value="Terminado", label="Terminada"),
                    ft.Radio(value="Recogido", label="Recogida"),
                ]
            ),
            value=current_status_ui,
        )

        # Horas (stepper)
        horas_val = [0]
        try:
            horas_val[0] = int(getattr(o, "horas", 0) or 0)
        except Exception:
            horas_val[0] = 0
        horas_text = ft.Text(str(horas_val[0]), width=26, text_align=ft.TextAlign.CENTER)

        def _menos(e):
            horas_val[0] = max(0, horas_val[0] - 1)
            horas_text.value = str(horas_val[0]); horas_text.update()

        def _mas(e):
            horas_val[0] += 1
            horas_text.value = str(horas_val[0]); horas_text.update()

        hours_stepper = ft.Row(
            [ft.IconButton(icon=ft.icons.REMOVE, on_click=_menos),
             ft.Container(width=60, alignment=ft.alignment.center, content=horas_text),
             ft.IconButton(icon=ft.icons.ADD, on_click=_mas)],
            alignment=ft.MainAxisAlignment.START,
        )

        def _guardar(e):
            marca = (tf_marca.value or "").strip()
            modelo = (tf_modelo.value or "").strip()
            tipo_id = _tipo_id_from_ui(dd_tipo.value or dd_tipo.label or "")
            status_id = _status_id_from_ui(rg_status.value)
            if not marca or not modelo or not tipo_id or not status_id:
                page.open(ft.SnackBar(ft.Text("Complete marca, modelo, tipo y estatus.")))
                return
            try:
                _update_orden_base(int(o.cve_orden), marca, int(tipo_id), modelo, int(status_id))
                try:
                    _actualizar_horas_orden(int(o.cve_orden), int(horas_val[0]))
                except Exception as ex:
                    print("WARN horas:", ex)
                connection.commit()
                _close_dialog(dlg)
                nonlocal status_cat
                status_cat = _status_catalog_from_db()
                llenar_tabla(True)
                page.open(ft.SnackBar(ft.Text("Orden actualizada con éxito")))
            except Exception as ex:
                try:
                    connection.rollback()
                except Exception:
                    pass
                page.open(ft.SnackBar(ft.Text(f"Error al guardar: {ex}")))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar Orden #{getattr(o, 'cve_orden', '')}"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    [tf_marca, dd_tipo, tf_modelo, ft.Text("Estado de la orden"), rg_status, ft.Text("Horas trabajadas"), hours_stepper],
                    tight=True,
                    height=360,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[ft.ElevatedButton("Guardar", on_click=_guardar), ft.OutlinedButton("Cancelar", on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        _open_dialog(dlg)

    # ===== Tabla =====
    encabezado_tabla = ft.Row(
        [
            ft.Text("Clave Orden", width=50, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Status", width=100, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Técnico", width=120, size=15, weight=ft.FontWeight.BOLD),
            ft.Text(" ", width=50, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Marca", width=100, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Modelo", width=100, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Tipo", width=100, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Cliente", width=120, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Editar Cliente", width=110, size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Editar Orden", width=110, size=15, weight=ft.FontWeight.BOLD),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    contenedor_ordenes = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def ver_tecnico(lista):
        if not lista:
            return ""
        return lista[0] if len(lista) == 1 else f"{lista[0]}..."

    def _resumir(o) -> str:
        return f"{getattr(o,'cve_orden','')} {getattr(o,'eq_modelo','')} {getattr(o,'cliente','')}"

    def llenar_tabla(cambio_dir: bool = False):
        contenedor_ordenes.controls.clear()
        try:
            ordenes = db_instance.ordenes() or []
        except Exception:
            ordenes = []
        data = list(reversed(ordenes)) if cambio_dir or btn_dir.selected else ordenes

        tipos_cat = _tipos_catalogo()  # id -> nombre

        for o in data:
            nombre_status_ui = _ui_status_name(getattr(o, "cve_status", None))
            pasa_estado = (filtro_estado.value == "Todos") or (nombre_status_ui == filtro_estado.value)
            pasa_taller = (str(filtro_taller.value) == "0") or (str(getattr(o, "cve_taller", "")) == str(filtro_taller.value))
            if not (pasa_estado and pasa_taller):
                continue

            try:
                tipo_nombre = tipos_cat.get(getattr(o, "cve_tipo_equipo", None), "")
            except Exception:
                tipo_nombre = ""

            fila = ft.Row(
                [
                    ft.Text(str(getattr(o, "cve_orden", "")), width=50),
                    _status_chip(nombre_status_ui),
                    ft.Text(ver_tecnico(getattr(o, "tecnicos", [])), width=120),
                    ft.IconButton(icon=ft.icons.REMOVE_RED_EYE, on_click=lambda e, oo=o: open_tecnicos_taller_dialog(oo), width=50),
                    ft.Text(getattr(o, "eq_marca", ""), width=100),
                    ft.Text(getattr(o, "eq_modelo", ""), width=100),
                    ft.Text(tipo_nombre, width=100),
                    ft.Text(str(getattr(o, "cliente", "")), width=120),
                    ft.IconButton(icon=ft.icons.EDIT, on_click=lambda e, oo=o: open_edit_client_dialog(oo), width=110),
                    ft.IconButton(icon=ft.icons.EDIT, on_click=lambda e, oo=o: open_edit_order_dialog(oo), width=110),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                height=50,
            )
            contenedor_ordenes.controls += [fila, ft.Divider()]

        page.update()

    def _refresh_orders_and_table():
        """Recarga y repinta después de operaciones en partes/servicios/notas."""
        nonlocal status_cat
        try:
            status_cat = _status_catalog_from_db()
        except Exception:
            pass
        llenar_tabla(True)

    filtro_estado.on_change = lambda e: llenar_tabla()
    filtro_taller.on_change = lambda e: llenar_tabla()
    llenar_tabla(False)

    # ====== OVERRIDES: Partes / Servicios con commit+refresh inmediato ======
    def open_nueva_parte_dialog(page_: ft.Page, db_: any, conn_: any):
        error = ft.Text('', color=ft.colors.RED)

        try:
            _ordenes = db_.ordenes() or []
        except Exception:
            _ordenes = []

        if not _ordenes:
            page_.open(ft.SnackBar(ft.Text("No hay órdenes para asociar la parte.")))
            return

        ordenes_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(text=_resumir(o), key=str(o.cve_orden)) for o in _ordenes],
            label="Seleccione la orden",
            value=str(_ordenes[0].cve_orden),
            width=420,
        )

        def _pieza_txt(n: dict) -> str:
            return f"{n['cve_parte']} {(n.get('part_no') or '')} {n['descripcion']} ${n['precio']}"

        try:
            piezas = db_.partes() or []
        except Exception:
            piezas = []

        piezas_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(text=_pieza_txt(n), key=str(n['cve_parte'])) for n in piezas],
            label='Seleccione la pieza',
            width=420,
        )

        def guardar(e=None):
            if ordenes_dropdown.value and piezas_dropdown.value:
                try:
                    db_.parte_orden(int(ordenes_dropdown.value), int(piezas_dropdown.value))
                    conn_.commit()
                    _close_dialog(dlg)
                    _refresh_orders_and_table()
                    page_.open(ft.SnackBar(ft.Text('Parte agregada con éxito')))
                except Exception as ex:
                    try:
                        conn_.rollback()
                    except Exception:
                        pass
                    error.value = f'Error al agregar la parte: {ex}'
                    page_.update()
            else:
                error.value = 'Seleccione todos los campos'
                page_.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text('Añadir nueva parte a orden'),
            content=ft.Column([ordenes_dropdown, piezas_dropdown, error], width=500),
            actions=[ft.ElevatedButton('Añadir', on_click=guardar),
                     ft.ElevatedButton('Cancelar', color=ft.colors.RED, on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )
        _open_dialog(dlg)

    def open_partes_dialog(page_: ft.Page, db_: any):
        contenedor = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=500)

        try:
            _ordenes = db_.ordenes() or []
        except Exception:
            _ordenes = []

        if not _ordenes:
            page_.open(ft.SnackBar(ft.Text("No hay órdenes.")))
            return

        ordenes_dd = ft.Dropdown(
            options=[ft.dropdown.Option(text=_resumir(o), key=str(o.cve_orden)) for o in _ordenes],
            label='Seleccione una orden:',
            width=520,
            value=str(_ordenes[0].cve_orden),
        )

        def _item_parte(p: dict) -> ft.Control:
            txt = f"{p['cve_orden_parte']}# {(p.get('part_no') or '')} ${p['precio']}\n{p['descripcion']}"
            return ft.Container(
                ft.Row(
                    [ft.Text(txt, size=16),
                     ft.IconButton(icon=ft.icons.DELETE_FOREVER_ROUNDED,
                                   icon_color=ft.colors.PINK_ACCENT,
                                   on_click=lambda e, n=p: eliminar(n))],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            )

        def actualizar(e=None):
            contenedor.controls.clear()
            try:
                partes = db_.partes_orden(int(ordenes_dd.value)) or []
            except Exception:
                partes = []
            for p in partes:
                contenedor.controls.append(_item_parte(p))
            if not partes:
                contenedor.controls.append(ft.Text("Sin partes en esta orden.", italic=True, color=ft.colors.GREY))
            page_.update()

        def eliminar(p):
            try:
                db_.eliminar_parte(p['cve_orden_parte'])
                connection.commit()
                _refresh_orders_and_table()
                actualizar()
                page_.open(ft.SnackBar(ft.Text('Parte eliminada')))
            except Exception as ex:
                try:
                    connection.rollback()
                except Exception:
                    pass
                page_.open(ft.SnackBar(ft.Text(f'Error al eliminar: {ex}')))

        ordenes_dd.on_change = actualizar

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Partes por orden"),
            content=ft.Column([ordenes_dd, contenedor], width=540, height=320),
            actions=[ft.ElevatedButton("Cerrar", on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )
        _open_dialog(dlg)
        actualizar()

    def open_nuevo_servicio_dialog(page_: ft.Page, db_: any, conn_: any):
        error = ft.Text('', color=ft.colors.RED)

        try:
            _ordenes = db_.ordenes() or []
        except Exception:
            _ordenes = []

        if not _ordenes:
            page_.open(ft.SnackBar(ft.Text("No hay órdenes para asociar el servicio.")))
            return

        ordenes_dd = ft.Dropdown(
            options=[ft.dropdown.Option(text=_resumir(o), key=str(o.cve_orden)) for o in _ordenes],
            label="Orden",
            width=420,
            value=str(_ordenes[0].cve_orden),
        )

        def _serv_txt(s: dict) -> str:
            return f"{s['cve_servicio']} ${s['precio']} {s['descripcion']}"

        try:
            servs = db_.servicios() or []
        except Exception:
            servs = []

        servicios_dd = ft.Dropdown(
            options=[ft.dropdown.Option(text=_serv_txt(s), key=str(s['cve_servicio'])) for s in servs],
            label='Servicio',
            width=420,
        )

        def guardar(e=None):
            if ordenes_dd.value and servicios_dd.value:
                try:
                    db_.servicio_orden(int(ordenes_dd.value), int(servicios_dd.value))
                    conn_.commit()
                    _close_dialog(dlg)
                    _refresh_orders_and_table()
                    page_.open(ft.SnackBar(ft.Text('Servicio agregado con éxito')))
                except Exception as ex:
                    try:
                        conn_.rollback()
                    except Exception:
                        pass
                    error.value = f'Error al agregar el servicio: {ex}'
                    page_.update()
            else:
                error.value = 'Seleccione todos los campos'
                page_.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text('Añadir nuevo servicio a orden'),
            content=ft.Column([ordenes_dd, servicios_dd, error], width=500),
            actions=[ft.ElevatedButton('Añadir', on_click=guardar),
                     ft.ElevatedButton('Cancelar', color=ft.colors.RED, on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )
        _open_dialog(dlg)

    def open_servicios_dialog(page_: ft.Page, db_: any):
        contenedor = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, width=500)

        try:
            _ordenes = db_.ordenes() or []
        except Exception:
            _ordenes = []

        if not _ordenes:
            page_.open(ft.SnackBar(ft.Text("No hay órdenes.")))
            return

        ordenes_dd = ft.Dropdown(
            options=[ft.dropdown.Option(text=_resumir(o), key=str(o.cve_orden)) for o in _ordenes],
            label='Seleccione una orden:',
            width=520,
            value=str(_ordenes[0].cve_orden),
        )

        def _item_serv(s: dict) -> ft.Control:
            txt = f"{s['cve_orden_servicio']}#  ${s['precio']}\n{s['descripcion']}"
            return ft.Container(
                ft.Row(
                    [ft.Text(txt, size=16),
                     ft.IconButton(icon=ft.icons.DELETE_FOREVER_ROUNDED,
                                   icon_color=ft.colors.PINK_ACCENT,
                                   on_click=lambda e, n=s: eliminar(n))],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            )

        def actualizar(e=None):
            contenedor.controls.clear()
            try:
                servs = db_.servicios_orden(int(ordenes_dd.value)) or []
            except Exception:
                servs = []
            for s in servs:
                contenedor.controls.append(_item_serv(s))
            if not servs:
                contenedor.controls.append(ft.Text("Sin servicios en esta orden.", italic=True, color=ft.colors.GREY))
            page_.update()

        def eliminar(s):
            try:
                db_.eliminar_servicio(s['cve_orden_servicio'])
                connection.commit()
                _refresh_orders_and_table()
                actualizar()
                page_.open(ft.SnackBar(ft.Text('Servicio eliminado')))
            except Exception as ex:
                try:
                    connection.rollback()
                except Exception:
                    pass
                page_.open(ft.SnackBar(ft.Text(f'Error al eliminar: {ex}')))

        ordenes_dd.on_change = actualizar

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Servicios por orden"),
            content=ft.Column([ordenes_dd, contenedor], width=540, height=320),
            actions=[ft.ElevatedButton("Cerrar", on_click=lambda e: _close_dialog(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )
        _open_dialog(dlg)
        actualizar()

    # ===== Tarjetas =====
    permisos = user.permisos()

    def nueva_orden(e=None):
        def _refrescar():
            try:
                llenar_tabla(True)
            except Exception:
                pass
        page.views.append(build_new_order_view(page, db_instance, connection, on_saved=_refrescar))
        page.go("/nueva")
        page.update()

    card_orden = ft.Container(
        bgcolor=ft.colors.LIGHT_BLUE_600,
        padding=20,
        border_radius=5,
        width=300,
        content=ft.Column(
            [
                ft.Text("Orden", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Obtener Reporte", on_click=lambda e: open_reporte_dialog(page, db_instance), visible=permisos.get("Reporte", True)),
                        ft.ElevatedButton("Nueva", on_click=nueva_orden, visible=permisos.get("Nueva_Orden", True)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ]
        ),
    )

    card_parte = ft.Container(
        bgcolor=ft.colors.LIGHT_BLUE_600,
        padding=20,
        border_radius=5,
        width=300,
        content=ft.Column(
            [
                ft.Text("Parte", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nueva", on_click=lambda e: open_nueva_parte_dialog(page, db_instance, connection), visible=permisos.get("Nueva_Parte", True)),
                        ft.ElevatedButton("Ver/Editar", on_click=lambda e: open_partes_dialog(page, db_instance), visible=permisos.get("Ver_Parte", True)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ]
        ),
    )

    card_servicio = ft.Container(
        bgcolor=ft.colors.LIGHT_BLUE_600,
        padding=20,
        border_radius=5,
        width=300,
        content=ft.Column(
            [
                ft.Text("Servicio", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nuevo", on_click=lambda e: open_nuevo_servicio_dialog(page, db_instance, connection), visible=permisos.get("Nuevo_Servicio", True)),
                        ft.ElevatedButton("Ver/Editar", on_click=lambda e: open_servicios_dialog(page, db_instance), visible=permisos.get("Ver_Servicio", True)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ]
        ),
    )

    card_nota = ft.Container(
        bgcolor=ft.colors.LIGHT_BLUE_600,
        padding=20,
        border_radius=5,
        width=300,
        content=ft.Column(
            [
                ft.Text("Nota", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Nueva", on_click=lambda e: open_nueva_nota_dialog(page, db_instance, connection), visible=permisos.get("Nueva_Nota", True)),
                        ft.ElevatedButton("Ver", on_click=lambda e: open_notas_dialog(page, db_instance), visible=permisos.get("Ver_Nota", True)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ]
        ),
    )

    # ===== View =====
    return ft.View(
        "/dashboard",
        controls=[
            usuario_info,
            ft.Divider(),
            ft.Row([card_orden, card_parte, card_servicio, card_nota], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ft.Divider(height=20, thickness=1),
            filtros,  # ← aquí ya aparece el botón "Gráfica" junto a la flecha
            encabezado_tabla,
            contenedor_ordenes,
        ],
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )