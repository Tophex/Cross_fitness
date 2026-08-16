"""
renovaciones_view.py — Registro de pagos y renovación de membresías (conectado a SQLite).

Flujo:
  1. Al montarse, carga la lista de clientes y planes para los Dropdowns.
  2. Carga el historial de membresías en el DataTable.
  3. Al registrar, valida la selección, llama a crear_membresia(), recarga el historial
     y muestra un SnackBar de éxito con la fecha calculada.

Compatibilidad: Flet 0.86+ | sqlite3 (stdlib)
"""

import flet as ft
from datetime import datetime

from database.db_manager import (
    obtener_clientes_para_dropdown,
    obtener_planes,
    buscar_clientes,
    programar_congelamiento,
    reactivar_membresia,
    get_connection,
    crear_membresia,
    obtener_historial_membresias,
)
from utils.pdf_manager import generar_recibo_pdf
from typing import Callable

def RenovacionesView(require_auth: Callable = None) -> ft.Control:
    """
    Vista de Renovaciones y Membresías.
    """

    _bg     = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _fbg    = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _dd_bg  = "#1C1D22" # Fondo sólido para que el menú del Dropdown no sea traslúcido
    _fbrd   = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _hdr_bg = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)

    # ── Búsqueda predictiva de clientes ────────────────────────────
    # Estado interno: ID del cliente actualmente seleccionado
    _selected_cliente_id = [None]  # lista mutable para capturar en closures

    # Campo de texto para buscar por cédula o nombre
    busqueda_tf = ft.TextField(
        hint_text="Buscar por cédula o nombre…",
        prefix_icon=ft.Icons.PERSON_SEARCH_ROUNDED,
        border_radius=10,
        bgcolor=_fbg,
        border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        cursor_color=ft.Colors.CYAN_400,
        expand=True,
    )

    # Etiqueta que muestra el cliente confirmado
    cliente_seleccionado_label = ft.Text(
        "", size=11, color=ft.Colors.CYAN_300, visible=False,
        weight=ft.FontWeight.W_500,
    )

    # Lista flotante de sugerencias
    sugerencias_col = ft.Column(spacing=0, tight=True)
    sugerencias_container = ft.Container(
        content=sugerencias_col,
        bgcolor=ft.Colors.with_opacity(0.97, "#1a1a2e"),
        border_radius=ft.BorderRadius(0, 0, 10, 10),
        border=ft.Border(
            left=ft.BorderSide(1, _fbrd), right=ft.BorderSide(1, _fbrd),
            bottom=ft.BorderSide(1, _fbrd), top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
        ),
        visible=False,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )

    def _hide_sugerencias():
        sugerencias_container.visible = False
        sugerencias_col.controls.clear()

    def _on_busqueda_change(e: ft.ControlEvent):
        texto = busqueda_tf.value.strip()
        _selected_cliente_id[0] = None
        cliente_seleccionado_label.visible = False

        if len(texto) < 1:
            _hide_sugerencias()
            e.page.update()
            return

        resultados = buscar_clientes(texto)[:8]  # máximo 8 sugerencias

        if not resultados:
            sugerencias_col.controls = [
                ft.Container(
                    content=ft.Text("Sin resultados", size=12, color=ft.Colors.WHITE38,
                                    italic=True),
                    padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                )
            ]
            sugerencias_container.visible = True
            e.page.update()
            return

        def _make_option(cliente):
            cid   = cliente["id"]
            label = f"{cliente['cedula']}  —  {cliente['nombre']}"

            def _select(ev, c_id=cid, c_label=label, c_nombre=cliente["nombre"]):
                _selected_cliente_id[0] = c_id
                busqueda_tf.value = c_label
                cliente_seleccionado_label.value   = f"✓  {c_nombre}"
                cliente_seleccionado_label.visible = True
                busqueda_tf.border_color = _fbrd
                _hide_sugerencias()
                ev.page.update()

            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED,
                                size=15, color=ft.Colors.CYAN_400),
                        ft.Text(label, size=13, color=ft.Colors.WHITE,
                                weight=ft.FontWeight.W_400),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding(left=12, top=9, right=12, bottom=9),
                on_click=_select,
                on_hover=lambda ev: (
                    setattr(ev.control, "bgcolor",
                            ft.Colors.with_opacity(0.15, ft.Colors.CYAN_400)
                            if ev.data == "true" else ft.Colors.TRANSPARENT),
                    ev.page.update(),
                ),
                ink=True,
                border=ft.Border(
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.07, ft.Colors.WHITE))
                ),
            )

        sugerencias_col.controls = [_make_option(c) for c in resultados]
        sugerencias_container.visible = True
        e.page.update()

    busqueda_tf.on_change = _on_busqueda_change

    # Stack para superponer la lista de sugerencias debajo del campo
    cliente_search_widget = ft.Column(
        controls=[busqueda_tf, sugerencias_container, cliente_seleccionado_label],
        spacing=0,
        expand=True,
    )

    plan_dropdown = ft.Dropdown(
        hint_text="Seleccionar Plan",
        leading_icon=ft.Icons.CARD_MEMBERSHIP_ROUNDED,
        border_radius=10, bgcolor=_dd_bg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        width=250,
    )
    
    error_label = ft.Text("", size=12, color=ft.Colors.RED_400, visible=False)

    # ── DataTable Historial ────────────────────────────────────────
    tabla_historial = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID",         size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Cliente",    size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Plan",       size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Inicio",     size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Vence",      size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Estado",     size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Acciones",   size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=_hdr_bg,
        border_radius=12,
        data_row_max_height=52,
        expand=True,
    )
    table_body = ft.Column(expand=True)

    # ── Helpers ────────────────────────────────────────────────────
    def _show_snack(page: ft.Page, msg: str, color):
        snack = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.with_opacity(0.92, color),
            duration=4000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _build_rows(page: ft.Page, busqueda: str = None):
        historial = obtener_historial_membresias(busqueda)
        filas = []

        for h in historial:
            mid = h["id"]
            estado = h["estado"]
            estado_color = ft.Colors.GREEN_400 if estado == "ACTIVA" else (ft.Colors.ORANGE_400 if estado == "SUSPENDIDA" else ft.Colors.RED_400)
            
            acciones = []
            if estado == "ACTIVA":
                def _on_congelar(e, m_id=mid):
                    justificacion_tf = ft.TextField(label="Justificación", multiline=True, min_lines=2, border_color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE), color=ft.Colors.WHITE)
                    
                    fecha_inicio_dp = ft.DatePicker(
                        first_date=datetime.now(),
                        help_text="Seleccionar fecha de inicio"
                    )
                    fecha_fin_dp = ft.DatePicker(
                        first_date=datetime.now(),
                        help_text="Seleccionar fecha de fin"
                    )
                    e.page.overlay.extend([fecha_inicio_dp, fecha_fin_dp])
                    
                    lbl_inicio = ft.Text(datetime.now().date().strftime("%Y-%m-%d"), color=ft.Colors.WHITE70)
                    lbl_fin = ft.Text("Indefinido", color=ft.Colors.WHITE70)
                    
                    def change_inicio(ev):
                        if fecha_inicio_dp.value:
                            lbl_inicio.value = fecha_inicio_dp.value.strftime("%Y-%m-%d")
                            fecha_fin_dp.first_date = fecha_inicio_dp.value
                        ev.page.update()
                        
                    def change_fin(ev):
                        if fecha_fin_dp.value:
                            lbl_fin.value = fecha_fin_dp.value.strftime("%Y-%m-%d")
                        ev.page.update()

                    fecha_inicio_dp.on_change = change_inicio
                    fecha_fin_dp.on_change = change_fin
                    
                    btn_inicio = ft.ElevatedButton("Inicio", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: setattr(fecha_inicio_dp, "open", True) or e.page.update())
                    btn_fin = ft.ElevatedButton("Fin", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: setattr(fecha_fin_dp, "open", True) or e.page.update())
                    btn_fin.disabled = True
                    
                    def toggle_indef(ev):
                        btn_fin.disabled = indefinido_cb.value
                        if indefinido_cb.value:
                            lbl_fin.value = "Indefinido"
                        else:
                            lbl_fin.value = fecha_fin_dp.value.strftime("%Y-%m-%d") if fecha_fin_dp.value else "No seleccionada"
                        ev.page.update()
                        
                    indefinido_cb = ft.Checkbox(label="Fin Indefinido", value=True, on_change=toggle_indef)
                    
                    def confirm(ev):
                        inicio_val = fecha_inicio_dp.value.strftime("%Y-%m-%d") if fecha_inicio_dp.value else datetime.now().date().strftime("%Y-%m-%d")
                        fin_val = None
                        if not indefinido_cb.value and fecha_fin_dp.value:
                            fin_val = fecha_fin_dp.value.strftime("%Y-%m-%d")
                            
                        try:
                            programar_congelamiento(m_id, justificacion_tf.value or "Sin justificación", inicio_val, fin_val)
                            dialog.open = False
                            _refresh(ev.page)
                            _show_snack(ev.page, "⏸ Congelamiento programado.", ft.Colors.ORANGE_900)
                        except Exception as ex:
                            _show_snack(ev.page, f"Error: {ex}", ft.Colors.RED_900)

                    def cancel(ev):
                        dialog.open = False
                        ev.page.update()

                    dialog = ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Congelar Membresía", weight=ft.FontWeight.BOLD),
                        content=ft.Column([
                            justificacion_tf,
                            ft.Row([btn_inicio, lbl_inicio]),
                            ft.Row([btn_fin, lbl_fin]),
                            indefinido_cb
                        ], tight=True, spacing=10),
                        actions=[
                            ft.TextButton("Cancelar", on_click=cancel),
                            ft.TextButton("Confirmar", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.ORANGE_400))
                        ],
                        bgcolor="#1A1D24",
                    )
                    e.page.overlay.append(dialog)
                    dialog.open = True
                    e.page.update()

                acciones.append(
                    ft.IconButton(ft.Icons.PAUSE_ROUNDED, icon_size=18, icon_color=ft.Colors.ORANGE_400, tooltip="Congelar", on_click=_on_congelar)
                )
            elif estado == "SUSPENDIDA":
                def _on_reactivar(e, m_id=mid):
                    try:
                        res = reactivar_membresia(m_id)
                        _refresh(e.page)
                        _show_snack(e.page, f"▶ Membresía reactivada. Nuevo vencimiento: {res['fecha_vencimiento']}", ft.Colors.GREEN_900)
                    except Exception as ex:
                        _show_snack(e.page, f"Error: {ex}", ft.Colors.RED_900)
                        
                acciones.append(
                    ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_size=18, icon_color=ft.Colors.GREEN_400, tooltip="Reactivar", on_click=_on_reactivar)
                )

            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(mid), color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text(h["cliente_nombre"], color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(h["plan_nombre"],    color=ft.Colors.CYAN_300)),
                    ft.DataCell(ft.Text(h["fecha_inicio"],   color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(h["fecha_vencimiento"], color=ft.Colors.WHITE70)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(estado, size=10, weight=ft.FontWeight.BOLD, color=estado_color),
                            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                            border_radius=6,
                            bgcolor=ft.Colors.with_opacity(0.12, estado_color)
                        )
                    ),
                    ft.DataCell(ft.Row(controls=acciones, spacing=0)),
                ])
            )
            
        tabla_historial.rows = filas

        if filas:
            table_body.controls = [tabla_historial]
        else:
            table_body.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY_ROUNDED, size=52, color=ft.Colors.WHITE24),
                            ft.Text("No hay membresías registradas.", size=14, color=ft.Colors.WHITE38,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    ),
                    padding=ft.Padding(left=0, top=40, right=0, bottom=40),
                    alignment=ft.Alignment(0, 0),
                )
            ]

    def _refresh(page: ft.Page):
        _build_rows(page, search_tf.value)
        page.update()

    def _clear_form():
        _selected_cliente_id[0]            = None
        busqueda_tf.value                  = ""
        busqueda_tf.border_color           = _fbrd
        cliente_seleccionado_label.visible = False
        _hide_sugerencias()
        plan_dropdown.value                = None
        error_label.visible                = False
        plan_dropdown.border_color         = _fbrd
        fecha_inicio_seleccionada[0]       = None
        fecha_inicio_label.value           = "Inicio: Hoy (YYYY-MM-DD)"

    def on_register(e: ft.ControlEvent):
        page = e.page
        cliente_id = _selected_cliente_id[0]
        plan_id    = plan_dropdown.value

        # Validación
        has_error = False
        if not cliente_id:
            busqueda_tf.border_color = ft.Colors.RED_400
            has_error = True
        else:
            busqueda_tf.border_color = _fbrd

        if not plan_id:
            plan_dropdown.border_color = ft.Colors.RED_400
            has_error = True
        else:
            plan_dropdown.border_color = _fbrd

        if has_error:
            error_label.value = "Selecciona un cliente y un plan."
            error_label.visible = True
            page.update()
            return

        try:
            resultado = crear_membresia(int(cliente_id), int(plan_id), fecha_inicio_seleccionada[0])
            
            # Obtener datos para PDF
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT cedula, nombre FROM clientes WHERE id = ?", (int(cliente_id),))
                c_data = cur.fetchone()
                cur.execute("SELECT nombre, precio FROM planes WHERE id = ?", (int(plan_id),))
                p_data = cur.fetchone()
            
            try:
                generar_recibo_pdf(
                    nombre_cliente=c_data["nombre"],
                    cedula=c_data["cedula"],
                    nombre_plan=p_data["nombre"],
                    precio=p_data["precio"],
                    fecha_inicio=resultado["fecha_inicio"],
                    fecha_vencimiento=resultado["fecha_vencimiento"]
                )
                pdf_msg = " Generando recibo..."
            except Exception as e_pdf:
                pdf_msg = f" (Error PDF: {e_pdf})"

            _clear_form()
            _refresh(page)
            _show_snack(page, f"✅  Pago registrado exitosamente.{pdf_msg}", ft.Colors.GREEN_900)
        except Exception as ex:
            error_label.value = f"Error al guardar: {ex}"
            error_label.visible = True
            page.update()

    # ── Calendario de Fecha de Inicio ──────────────────────────────
    fecha_inicio_seleccionada = [None]
    fecha_inicio_label = ft.Text("Inicio: Hoy (YYYY-MM-DD)", size=13, color=ft.Colors.WHITE70)

    def on_date_change(e):
        if e.control.value:
            fecha_str = e.control.value.strftime("%Y-%m-%d")
            fecha_inicio_seleccionada[0] = fecha_str
            fecha_inicio_label.value = f"Inicio: {fecha_str}"
        else:
            fecha_inicio_seleccionada[0] = None
            fecha_inicio_label.value = "Inicio: Hoy (YYYY-MM-DD)"
        fecha_inicio_label.update()

    dp_inicio = ft.DatePicker(on_change=on_date_change)

    def on_calendar_click(e):
        if dp_inicio not in e.page.overlay:
            e.page.overlay.append(dp_inicio)
        dp_inicio.open = True
        e.page.update()

    btn_calendario = ft.IconButton(
        icon=ft.Icons.CALENDAR_TODAY_ROUNDED,
        icon_color=ft.Colors.CYAN_400,
        on_click=on_calendar_click,
        tooltip="Seleccionar fecha de inicio"
    )

    fila_fecha_inicio = ft.Row(
        controls=[fecha_inicio_label, btn_calendario],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Botón Registrar ────────────────────────────────────────────
    register_btn = ft.Button(
        "Registrar Pago o Activar Membresía",
        icon=ft.Icons.PAYMENTS_ROUNDED,
        on_click=on_register,
        bgcolor=ft.Colors.CYAN_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=24, top=14, right=24, bottom=14),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    # ── Contenedor del Formulario ──────────────────────────────────
    form_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Nueva Renovación", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row(controls=[cliente_search_widget, plan_dropdown], spacing=10),
                error_label,
                ft.Row(
                    controls=[fila_fecha_inicio, register_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
            ],
            spacing=8,
        ),
        padding=ft.Padding(left=20, top=18, right=20, bottom=18),
        border_radius=14,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
    )

    # ── Contenedor de Historial ────────────────────────────────────
    search_tf = ft.TextField(
        hint_text="Buscar cliente por cédula o nombre...",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: (_build_rows(e.page, e.control.value), e.page.update()),
        border_radius=10,
        bgcolor=_fbg,
        border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE,
        height=40,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0)
    )

    history_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, size=18, color=ft.Colors.CYAN_400),
                        ft.Text("Últimas Renovaciones", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                search_tf,
                ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                table_body,
            ],
            expand=True,
        ),
        padding=ft.Padding(left=20, top=18, right=20, bottom=18),
        border_radius=14,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
        expand=True,
    )

    # ── Carga inicial estática ─────────────────────────────────────
    
    # (El campo de búsqueda de clientes no necesita pre-carga; busca en tiempo real)
    
    planes_list = obtener_planes()
    plan_dropdown.options = [
        ft.dropdown.Option(key=str(p["id"]), text=f"{p['nombre']} (${p['precio']:,.2f})") 
        for p in planes_list
    ]
    
    # Cargar historial
    _build_rows(None)  # En la inicialización page es None, _build_rows no usa page de todos modos, solo _show_snack en caso de error/eliminar
    
    # ── Layout principal ───────────────────────────────────────────
    return ft.Column(
        controls=[
            ft.Text("Caja", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Renovaciones", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            form_container,
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            history_container,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
