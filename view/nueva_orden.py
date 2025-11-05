# view/nueva_orden.py
from __future__ import annotations
import re
import flet as ft

# Compat Flet
if not hasattr(ft, "colors") and hasattr(ft, "Colors"):
    ft.colors = ft.Colors
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
PHONE_10_RE = re.compile(r"^\d{10}$")
PHONE_PLUS52_RE = re.compile(r"^\+52\d{10}$")
HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)

def normalize_mx_phone_strict(raw: str) -> str | None:
    s = (raw or "").strip()
    if PHONE_10_RE.fullmatch(s):
        return s
    if PHONE_PLUS52_RE.fullmatch(s):
        return s[-10:]
    return None

def _normalize_house(s: str) -> str:
    s = (s or "").strip().upper().replace(" ", "")
    s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
    if s in ("SN", "S-N"):
        s = "S/N"
    return s

def _int_or_none(v):
    try:
        return int(str(v).strip())
    except Exception:
        return None

def _as_id_name_dict(data) -> dict[int, str]:
    """
    Normaliza dicts o listas/tuplas/dicts en forma {id:int -> nombre:str}
    """
    out: dict[int, str] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            # caso id->nombre
            if isinstance(k, (int, str)) and str(k).strip().isdigit():
                try:
                    out[int(k)] = str(v)
                    continue
                except Exception:
                    pass
            # caso nombre->id
            if isinstance(v, (int, str)) and str(v).strip().isdigit():
                try:
                    out[int(v)] = str(k)
                except Exception:
                    pass
    elif isinstance(data, (list, tuple)):
        for it in data:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                try:
                    out[int(it[0])] = str(it[1])
                except Exception:
                    pass
            elif isinstance(it, dict):
                _id = it.get("id") or it.get("cve") or it.get("cve_estado") or it.get("cve_pais") or it.get("cve_tipo_equipo")
                _nm = it.get("nombre") or it.get("descripcion")
                if _id is not None and _nm is not None:
                    try:
                        out[int(_id)] = str(_nm)
                    except Exception:
                        pass
    return out


def build_new_order_view(page: ft.Page, db_instance, connection, on_saved: callable | None = None) -> ft.View:
    page.title = "Nueva orden"

    # ===== Cliente =====
    tf_nombre  = ft.TextField(label="Nombre", expand=True, border_color=ft.colors.BLUE_300)
    tf_pat     = ft.TextField(label="Apellido Paterno", expand=True, border_color=ft.colors.BLUE_300)
    tf_mat     = ft.TextField(label="Apellido Materno", expand=True, border_color=ft.colors.BLUE_300)
    tf_correo  = ft.TextField(label="Correo", expand=True, border_color=ft.colors.BLUE_300, hint_text="ejemplo@dominio.com")
    tf_tel     = ft.TextField(label="Teléfono", expand=True, border_color=ft.colors.BLUE_300, hint_text="10 dígitos o +52 y 10 dígitos")

    tf_calle   = ft.TextField(label="Calle", expand=True, border_color=ft.colors.BLUE_300)
    tf_numero  = ft.TextField(label="Número de Calle", expand=True, border_color=ft.colors.BLUE_300, hint_text="1–6 dígitos / 123B / S/N")

    tf_cp      = ft.TextField(label="Código Postal", expand=True, border_color=ft.colors.BLUE_300)
    tf_colonia = ft.TextField(label="Colonia", expand=True, border_color=ft.colors.BLUE_300)
    tf_mpio    = ft.TextField(label="Municipio", expand=True, border_color=ft.colors.BLUE_300)

    # ===== País / Estado =====
    _paises = _as_id_name_dict(db_instance.paises() or {})
    dd_pais = ft.Dropdown(
        label="País",
        options=[ft.dropdown.Option(text=name, key=str(pid)) for pid, name in _paises.items()],
        expand=True
    )
    dd_estado = ft.Dropdown(label="Estado", options=[], expand=True, disabled=True)
    tf_estado_otro = ft.TextField(label="Nuevo Estado", expand=True, visible=False, border_color=ft.colors.BLUE_300)
    btn_estado_agregar = ft.ElevatedButton("Agregar estado", visible=False)

    def _estado_changed(e=None):
        is_otro = (dd_estado.value == "Otro")
        tf_estado_otro.visible = is_otro
        btn_estado_agregar.visible = is_otro
        page.update()

    def _refresh_estado_options(selected: str | None = None):
        """Reconstruye las opciones con UNA sola opción 'Otro' y los estados actuales de BD."""
        dd_estado.disabled = True
        options: list[ft.dropdown.Option] = [ft.dropdown.Option("Otro")]

        if dd_pais.value:
            try:
                estados = _as_id_name_dict(db_instance.estados(dd_pais.value) or {})
            except Exception as ex:
                print("WARN estados:", ex)
                estados = {}

            seen = set()
            for eid, name in estados.items():
                nm = str(name).strip()
                if not nm:
                    continue
                low = nm.lower()
                if low in seen:
                    continue
                options.append(ft.dropdown.Option(text=nm, key=str(eid)))
                seen.add(low)

        dd_estado.options = options
        valid_keys = {opt.key for opt in options if hasattr(opt, "key")}
        if selected is not None:
            dd_estado.value = selected if selected in valid_keys else "Otro"
        else:
            dd_estado.value = dd_estado.value if dd_estado.value in valid_keys else "Otro"

        dd_estado.disabled = False
        _estado_changed()
        page.update()

    def _load_estados(e=None):
        tf_estado_otro.visible = False
        btn_estado_agregar.visible = False
        _refresh_estado_options()

    def _agregar_estado_now(e=None):
        nombre_nuevo = (tf_estado_otro.value or "").strip()
        if not dd_pais.value:
            page.open(ft.SnackBar(ft.Text("Seleccione primero un país.")))
            return
        if not nombre_nuevo:
            page.open(ft.SnackBar(ft.Text("Escriba el nombre del nuevo estado.")))
            return

        try:
            new_id = db_instance.upsert_estado(_int_or_none(dd_pais.value), nombre_nuevo)
        except Exception as ex:
            print("WARN upsert_estado:", ex)
            new_id = None

        if new_id is None:
            page.open(ft.SnackBar(ft.Text("No se pudo agregar el estado. Intente de nuevo.")))
            return

        # Hacer visible inmediatamente y evitar duplicados:
        try:
            # Confirmamos el alta del catálogo para que quede disponible al recargar.
            connection.commit()
        except Exception:
            pass

        tf_estado_otro.value = ""
        tf_estado_otro.visible = False
        btn_estado_agregar.visible = False
        _refresh_estado_options(selected=str(new_id))
        page.open(ft.SnackBar(ft.Text("Estado agregado.")))

    dd_pais.on_change = _load_estados
    dd_estado.on_change = _estado_changed
    btn_estado_agregar.on_click = _agregar_estado_now

    # ===== Validaciones live =====
    def _email_live(e=None):
        v = (tf_correo.value or "").strip()
        tf_correo.error_text = None if (v and EMAIL_RE.match(v)) else "Correo no válido"
        page.update()

    def _tel_live(e=None):
        raw = (tf_tel.value or "").strip()
        ok = PHONE_10_RE.fullmatch(raw) or PHONE_PLUS52_RE.fullmatch(raw)
        tf_tel.error_text = None if ok else "Use 10 dígitos o +52 y 10 dígitos"
        page.update()

    def _num_live(e=None):
        val = _normalize_house(tf_numero.value)
        tf_numero.value = val
        tf_numero.error_text = None if (val and HOUSE_RE.match(val)) else "1–6 dígitos, opcional letra (123B) o 'S/N'"
        page.update()

    def _cp_live(e=None):
        raw = (tf_cp.value or "")
        tf_cp.value = "".join(ch for ch in raw if ch.isdigit())[:5]
        page.update()

    tf_correo.on_change = _email_live
    tf_tel.on_change = _tel_live
    tf_numero.on_change = _num_live
    tf_cp.on_change = _cp_live

    # ===== Orden =====
    tf_marca  = ft.TextField(label="Marca", expand=True, border_color=ft.colors.BLUE_300)
    tf_modelo = ft.TextField(label="Modelo", expand=True, border_color=ft.colors.BLUE_300)

    _tipos = _as_id_name_dict(db_instance.tipos() or {})
    dd_tipo = ft.Dropdown(
        label="Tipo",
        options=[ft.dropdown.Option(text=name, key=str(tid)) for tid, name in _tipos.items()],
        expand=True
    )

    tf_nota = ft.TextField(label="Nota Inicial del Cliente", multiline=True, expand=True, border_color=ft.colors.BLUE_300)

    # ===== Técnico / Taller =====
    _talleres = _as_id_name_dict(db_instance.talleres() or {})
    dd_taller = ft.Dropdown(
        label="Taller",
        options=[ft.dropdown.Option(text=name, key=str(tid)) for tid, name in _talleres.items()],
        expand=True
    )
    dd_tecnico = ft.Dropdown(label="Técnico", options=[], expand=True, disabled=True)

    def _load_tecnicos(e=None):
        dd_tecnico.disabled = True
        dd_tecnico.options = []
        if dd_taller.value:
            try:
                tecnicos = db_instance.tecnicos_taller(dd_taller.value) or []
                dd_tecnico.options = [
                    ft.dropdown.Option(
                        text=f"{(t.get('nombre','') or '').strip()} {(t.get('paterno','') or '').strip()}".strip(),
                        key=str(t.get('cve_empleado'))
                    ) for t in tecnicos
                ]
                dd_tecnico.disabled = False
            except Exception as ex:
                print("WARN tecnicos:", ex)
        page.update()

    dd_taller.on_change = _load_tecnicos

    # ===== Acciones =====
    error = ft.Text("", color=ft.colors.RED)

    def cancelar(e=None):
        page.title = "Página principal"
        if page.views and page.views[-1].route == "/nueva":
            page.views.pop()
            page.go("/dashboard")
        else:
            page.go("/dashboard")
        page.update()

    def guardar_orden(e=None):
        error.value = ""
        tf_correo.error_text = None
        tf_tel.error_text = None
        tf_numero.error_text = None
        page.update()

        # Recolecta
        nombre   = (tf_nombre.value or "").strip()
        paterno  = (tf_pat.value or "").strip()
        materno  = (tf_mat.value or "").strip()
        correo   = (tf_correo.value or "").strip()
        tel_raw  = (tf_tel.value or "").strip()

        calle    = (tf_calle.value or "").strip()
        numero   = (tf_numero.value or "").strip()
        cp       = "".join(ch for ch in (tf_cp.value or "") if ch.isdigit())[:5]
        colonia_txt = (tf_colonia.value or "").strip()
        mpio     = (tf_mpio.value or "").strip()

        pais_val    = dd_pais.value
        estado_sel  = dd_estado.value
        estado_otro = (tf_estado_otro.value or "").strip()

        marca    = (tf_marca.value or "").strip()
        modelo   = (tf_modelo.value or "").strip()
        tipo     = dd_tipo.value
        nota     = (tf_nota.value or "").strip()
        taller   = dd_taller.value
        tecnico  = dd_tecnico.value

        if not all([nombre, paterno, correo, tel_raw, calle, numero, cp, colonia_txt, mpio, pais_val,
                    marca, modelo, tipo, nota, taller, tecnico]):
            error.value = "Llene todos los campos obligatorios."
            page.update()
            return

        if not EMAIL_RE.match(correo):
            tf_correo.error_text = "Correo no válido (ej. usuario@dominio.com)"
            error.value = "Corrija los campos marcados en rojo."
            page.update()
            return

        tel_norm = normalize_mx_phone_strict(tel_raw)
        if tel_norm is None:
            tf_tel.error_text = "Teléfono inválido: use 10 dígitos o +52 y 10 dígitos"
            error.value = "Corrija los campos marcados en rojo."
            page.update()
            return

        numero_norm = _normalize_house(numero)
        if not HOUSE_RE.match(numero_norm):
            tf_numero.error_text = "Número inválido (1–6 dígitos, opcional letra o 'S/N')"
            error.value = "Corrija los campos marcados en rojo."
            page.update()
            return

        # === Estado: si usuario dejó "Otro" + texto pero NO pulsó el botón, lo creamos ahora ===
        estado_id: int | None = None
        if estado_sel == "Otro":
            if not estado_otro:
                error.value = "Escriba el nombre del nuevo estado."
                page.update()
                return
            try:
                new_id = db_instance.upsert_estado(_int_or_none(pais_val), estado_otro)
            except Exception as ex:
                print("WARN upsert_estado(save):", ex)
                new_id = None

            if new_id is None:
                error.value = "No se pudo crear el estado. Intente de nuevo."
                page.update()
                return

            estado_id = int(new_id)
            try:
                connection.commit()
            except Exception:
                pass
        else:
            estado_id = _int_or_none(estado_sel)

        if not estado_id:
            error.value = "Seleccione un estado o escríbalo y agréguelo."
            page.update()
            return

        # === Colonia opcionalmente normalizada ===
        colonia_param = colonia_txt
        try:
            resolver_fn = getattr(db_instance, "resolve_or_create_colonia", None)
            if resolver_fn:
                cid = resolver_fn(
                    cp=cp,
                    nombre=colonia_txt,
                    municipio=(mpio or None),
                    estado=estado_id,
                    pais=_int_or_none(pais_val)
                )
                if not cid:
                    cid = resolver_fn(cp=cp, nombre=colonia_txt)
                if cid:
                    colonia_param = int(cid)
        except Exception as ex:
            print("WARN resolver_colonia:", ex)

        # ==== Guardar ====
        try:
            cli_id = db_instance.insertar_cliente_y_verificar_datos(
                nombre, paterno, materno, correo, tel_norm,
                calle, numero_norm, cp, colonia_param,
                mpio, estado_id, pais_val
            )
            if not cli_id:
                raise RuntimeError("No fue posible crear el cliente.")

            db_instance.insertar_orden(
                1,  # cve_status inicial
                marca,
                modelo,
                tipo,
                nota,
                cli_id,
                taller,
                tecnico
            )
            try:
                connection.commit()
            except Exception:
                pass

            page.open(ft.SnackBar(ft.Text("Orden creada con éxito")))
            if callable(on_saved):
                try:
                    on_saved()
                except Exception:
                    pass
            cancelar()

        except Exception as ex:
            try:
                connection.rollback()
            except Exception:
                pass
            error.value = f"Error al guardar: {ex}"
            page.update()

    # ===== UI =====
    return ft.View(
        "/nueva",
        controls=[ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Nueva Orden", size=24, weight=ft.FontWeight.BOLD),
                        error,
                        ft.Row([
                            ft.ElevatedButton("Guardar", on_click=guardar_orden),
                            ft.ElevatedButton("Cancelar", on_click=cancelar, color=ft.colors.RED),
                        ]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text("Información del Cliente", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(
                    [
                        ft.Row([tf_nombre, tf_pat, tf_mat]),
                        ft.Row([tf_correo, tf_tel]),
                        ft.Row([tf_calle, tf_numero, tf_cp]),
                        ft.Row([tf_colonia, tf_mpio]),
                        ft.Row([dd_pais, dd_estado, tf_estado_otro, btn_estado_agregar]),
                    ],
                    spacing=5,
                ),
                ft.Text("Información de la Orden", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(
                    [ft.Row([tf_marca, tf_modelo, dd_tipo]), tf_nota],
                    spacing=5,
                ),
                ft.Text("Técnico", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([dd_taller, dd_tecnico]),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.HIDDEN,
        )],
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )