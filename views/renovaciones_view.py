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

from database.db_manager import (
    obtener_clientes_para_dropdown,
    obtener_planes,
    crear_membresia,
    obtener_historial_membresias,
    buscar_clientes,
)

def RenovacionesView() -> ft.Control:
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

    def _build_rows(page: ft.Page):
        historial = obtener_historial_membresias()
        filas = []

        for h in historial:
            estado_color = ft.Colors.GREEN_400 if h["estado"] == "ACTIVA" else ft.Colors.RED_400
            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(h["id"]), color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text(h["cliente_nombre"], color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(h["plan_nombre"],    color=ft.Colors.CYAN_300)),
                    ft.DataCell(ft.Text(h["fecha_inicio"],   color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(h["fecha_vencimiento"], color=ft.Colors.WHITE70)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(h["estado"], size=10, weight=ft.FontWeight.BOLD, color=estado_color),
                            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                            border_radius=6,
                            bgcolor=ft.Colors.with_opacity(0.12, estado_color)
                        )
                    ),
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
        _build_rows(page)
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
            resultado = crear_membresia(int(cliente_id), int(plan_id))
            _clear_form()
            _refresh(page)
            _show_snack(page, f"✅  Membresía activada. Vence el {resultado['fecha_vencimiento']}.", ft.Colors.GREEN_900)
        except Exception as ex:
            error_label.value = f"Error al guardar: {ex}"
            error_label.visible = True
            page.update()

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
                ft.Row(controls=[register_btn], alignment=ft.MainAxisAlignment.END),
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
