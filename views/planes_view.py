"""
planes_view.py — Catálogo de Planes de membresía (conectado a SQLite).

Flujo:
  1. Al montarse, carga los planes con obtener_planes() y rellena el DataTable.
  2. Al hacer clic en 'Guardar Plan', valida los campos, llama a crear_plan(),
     recarga la tabla, limpia el formulario y muestra un SnackBar de éxito.
  3. El botón de eliminar en cada fila llama a eliminar_plan() y recarga la tabla.

Compatibilidad: Flet 0.86+ | sqlite3 (stdlib)
"""

import flet as ft
import sqlite3

from database.db_manager import crear_plan, obtener_planes, eliminar_plan


def PlanesView() -> ft.Control:
    """
    Vista del Catálogo de Planes con CRUD conectado a la BD.
    """

    _bg     = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _fbg    = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _fbrd   = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _hdr_bg = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)

    # ── Campos del formulario ──────────────────────────────────────
    nombre_field = ft.TextField(
        hint_text="Nombre del plan (ej. Mensual)",
        prefix_icon=ft.Icons.LABEL_ROUNDED,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        height=46, expand=True,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    dias_field = ft.TextField(
        hint_text="Días",
        prefix_icon=ft.Icons.CALENDAR_TODAY_ROUNDED,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        width=110, height=46,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    precio_field = ft.TextField(
        hint_text="Precio ($)",
        prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=10, bgcolor=_fbg, border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        width=130, height=46,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
    )
    error_label = ft.Text("", size=12, color=ft.Colors.RED_400, visible=False)

    # ── DataTable de planes ────────────────────────────────────────
    tabla_planes = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#",         size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Plan",      size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Días",      size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Precio",    size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Acciones",  size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=_hdr_bg,
        border_radius=12,
        data_row_max_height=52,
        expand=True,
    )

    # Contenedor que envuelve la tabla para mostrar el estado vacío
    table_body = ft.Column(expand=True)

    def _build_rows(page: ft.Page):
        """Consulta la BD y reconstruye las filas del DataTable."""
        planes = obtener_planes()
        filas = []

        for p in planes:
            plan_id  = p["id"]
            nombre   = p["nombre"]
            dias     = p["dias_duracion"]
            precio   = p["precio"]

            def _on_delete(e, pid=plan_id, pname=nombre):
                try:
                    eliminar_plan(pid)
                    _refresh(e.page)
                    _show_snack(e.page, f"Plan '{pname}' eliminado.", ft.Colors.ORANGE_900)
                except sqlite3.IntegrityError:
                    _show_snack(e.page, "No se puede eliminar: hay membresías vinculadas.", ft.Colors.RED_900)

            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(plan_id), color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text(nombre,       color=ft.Colors.WHITE,   weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(str(dias),    color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(f"${precio:,.2f}", color=ft.Colors.GREEN_300)),
                    ft.DataCell(
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_color=ft.Colors.RED_400,
                            icon_size=18,
                            tooltip="Eliminar plan",
                            on_click=_on_delete,
                        )
                    ),
                ])
            )

        tabla_planes.rows = filas

        if filas:
            table_body.controls = [tabla_planes]
        else:
            table_body.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.CARD_MEMBERSHIP_OUTLINED, size=52, color=ft.Colors.WHITE24),
                            ft.Text("No hay planes registrados aún.", size=14, color=ft.Colors.WHITE38,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    ),
                    padding=ft.Padding(left=0, top=40, right=0, bottom=40),
                    alignment=ft.Alignment(0, 0),
                )
            ]

    def _show_snack(page: ft.Page, msg: str, color):
        snack = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.with_opacity(0.92, color),
            duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _refresh(page: ft.Page):
        _build_rows(page)
        page.update()

    def _clear_form():
        nombre_field.value = ""
        dias_field.value   = ""
        precio_field.value = ""
        error_label.visible = False
        nombre_field.border_color = _fbrd
        dias_field.border_color   = _fbrd
        precio_field.border_color = _fbrd

    def on_save(e: ft.ControlEvent):
        page  = e.page
        nom   = (nombre_field.value or "").strip()
        dias  = (dias_field.value   or "").strip()
        prec  = (precio_field.value or "").strip()

        # Validación
        has_error = False
        for field, val in [(nombre_field, nom), (dias_field, dias), (precio_field, prec)]:
            if not val:
                field.border_color = ft.Colors.RED_400
                has_error = True
            else:
                field.border_color = _fbrd

        try:
            dias_int  = int(dias)  if dias  else 0
            prec_float = float(prec) if prec else -1
        except ValueError:
            has_error = True

        if has_error or dias_int <= 0 or prec_float < 0:
            error_label.value   = "Completa todos los campos correctamente."
            error_label.visible = True
            page.update()
            return

        try:
            crear_plan(nom, prec_float, dias_int)
            _clear_form()
            _refresh(page)
            _show_snack(page, f"✅  Plan '{nom}' guardado correctamente.", ft.Colors.GREEN_900)
        except sqlite3.Error as ex:
            error_label.value   = f"Error al guardar: {ex}"
            error_label.visible = True
            page.update()

    # ── Botón Guardar ──────────────────────────────────────────────
    save_btn = ft.Button(
        "Guardar Plan",
        icon=ft.Icons.ADD_CIRCLE_ROUNDED,
        on_click=on_save,
        bgcolor=ft.Colors.CYAN_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=24, top=12, right=24, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    # ── Formulario ─────────────────────────────────────────────────
    form_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Nuevo Plan", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row(controls=[nombre_field, dias_field, precio_field], spacing=10),
                error_label,
                ft.Row(controls=[save_btn], alignment=ft.MainAxisAlignment.END),
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

    # ── Sección tabla ──────────────────────────────────────────────
    table_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CARD_MEMBERSHIP_ROUNDED, size=18, color=ft.Colors.CYAN_400),
                        ft.Text("Planes registrados", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
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

    # ── Carga inicial sin page (se completa en did_mount) ──────────
    # Usamos un control contenedor raíz que dispara la carga al montarse.
    root = ft.Column(
        controls=[
            ft.Text("Catálogo", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Planes", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            form_container,
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            table_container,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    # La primera carga no tiene página todavía; la hacemos con un truco:
    # cargamos las filas vacías primero y al primer evento de página actualizamos.
    # La forma correcta en Flet es usar did_mount en un UserControl,
    # pero para compatibilidad máxima usamos una función on_mount en el Container raíz.

    def on_mount(e):
        _refresh(e.page)

    # Envolvemos en un Container con on_mount simulado mediante el truco
    # de un Container invisible que captura el primer evento de click/hover:
    # La solución compatible con Flet 0.86 sin UserControl es retornar
    # un Column que el navigate() de main.py llama; la primera vez que
    # la página hace page.update() (al agregarlo) el DataTable ya existe.
    # Cargamos las filas vacías ahora — se llenarán en el primer page.update().

    # ── Pre-carga estática (sin page, sin update) ─────────────────
    planes_iniciales = obtener_planes()
    filas_iniciales = []
    for p in planes_iniciales:
        plan_id = p["id"]
        nombre  = p["nombre"]
        dias    = p["dias_duracion"]
        precio  = p["precio"]

        def _on_del_init(e, pid=plan_id, pname=nombre):
            try:
                eliminar_plan(pid)
                _refresh(e.page)
                _show_snack(e.page, f"Plan '{pname}' eliminado.", ft.Colors.ORANGE_900)
            except sqlite3.IntegrityError:
                _show_snack(e.page, "No se puede eliminar: hay membresías vinculadas.", ft.Colors.RED_900)

        filas_iniciales.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(plan_id), color=ft.Colors.WHITE54)),
                ft.DataCell(ft.Text(nombre,       color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(str(dias),    color=ft.Colors.WHITE70)),
                ft.DataCell(ft.Text(f"${precio:,.2f}", color=ft.Colors.GREEN_300)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=ft.Colors.RED_400, icon_size=18, tooltip="Eliminar plan",
                        on_click=_on_del_init,
                    )
                ),
            ])
        )

    tabla_planes.rows = filas_iniciales
    if filas_iniciales:
        table_body.controls = [tabla_planes]
    else:
        table_body.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.CARD_MEMBERSHIP_OUTLINED, size=52, color=ft.Colors.WHITE24),
                        ft.Text("No hay planes registrados aún.", size=14, color=ft.Colors.WHITE38,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                ),
                padding=ft.Padding(left=0, top=40, right=0, bottom=40),
                alignment=ft.Alignment(0, 0),
            )
        ]

    return root
