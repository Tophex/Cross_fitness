"""
admin_view.py — Vista unificada de Administración.

Combina el Catálogo de Planes y los Reportes & Estadísticas en una única
pestaña con dos sub-tabs internos, reduciendo el número de ítems en el
Sidebar sin perder ninguna funcionalidad.

Tabs internos:
  0 → Planes     (CRUD de planes de membresía)
  1 → Reportes   (Estadísticas, historial de aperturas manuales, exportación CSV)

Fase 7 — Exportación CSV:
  AdminView acepta on_export_csv: Callable[[], None] opcional.
  Cuando el botón 'Exportar a Excel (CSV)' se presiona, invoca ese callback
  (definido en main.py) que abre el FilePicker y gestiona la escritura del archivo.

Compatibilidad: Flet 0.86+ | sqlite3 (stdlib)
"""

import flet as ft
import sqlite3
from datetime import datetime
from typing import Callable, Optional

from database.db_manager import (
    crear_plan, obtener_planes, eliminar_plan,
    obtener_aperturas_manuales, obtener_resumen_estadisticas,
    obtener_historial_ingresos_rango, obtener_historial_pagos_rango
)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN PLANES (extraída de planes_view.py)
# ══════════════════════════════════════════════════════════════════════════════

def _build_planes_tab() -> ft.Control:
    """Construye el contenido completo de la sub-pestaña de Planes."""

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
            ft.DataColumn(ft.Text("#",        size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Plan",     size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Días",     size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Precio",   size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Acciones", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=_hdr_bg,
        border_radius=12,
        data_row_max_height=52,
        expand=True,
    )
    table_body = ft.Column(expand=True)

    def _show_snack(page: ft.Page, msg: str, color):
        snack = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.with_opacity(0.92, color),
            duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _build_rows(page: ft.Page):
        planes = obtener_planes()
        filas = []
        for p in planes:
            plan_id = p["id"]
            nombre  = p["nombre"]
            dias    = p["dias_duracion"]
            precio  = p["precio"]

            def _on_delete(e, pid=plan_id, pname=nombre):
                try:
                    eliminar_plan(pid)
                    _build_rows(e.page)
                    e.page.update()
                    _show_snack(e.page, f"Plan '{pname}' eliminado.", ft.Colors.ORANGE_900)
                except sqlite3.IntegrityError:
                    _show_snack(e.page, "No se puede eliminar: hay membresías vinculadas.", ft.Colors.RED_900)

            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(plan_id), color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text(nombre,       color=ft.Colors.WHITE,  weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(str(dias),    color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(f"${precio:,.2f}", color=ft.Colors.GREEN_300)),
                    ft.DataCell(
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_color=ft.Colors.RED_400, icon_size=18,
                            tooltip="Eliminar plan", on_click=_on_delete,
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

    def _clear_form():
        nombre_field.value  = ""
        dias_field.value    = ""
        precio_field.value  = ""
        error_label.visible = False
        nombre_field.border_color = _fbrd
        dias_field.border_color   = _fbrd
        precio_field.border_color = _fbrd

    def on_save(e: ft.ControlEvent):
        page = e.page
        nom  = (nombre_field.value or "").strip()
        dias = (dias_field.value   or "").strip()
        prec = (precio_field.value or "").strip()

        has_error = False
        for field, val in [(nombre_field, nom), (dias_field, dias), (precio_field, prec)]:
            if not val:
                field.border_color = ft.Colors.RED_400
                has_error = True
            else:
                field.border_color = _fbrd
        try:
            dias_int   = int(dias)   if dias else 0
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
            _build_rows(page)
            page.update()
            _show_snack(page, f"✅  Plan '{nom}' guardado correctamente.", ft.Colors.GREEN_900)
        except sqlite3.Error as ex:
            error_label.value   = f"Error al guardar: {ex}"
            error_label.visible = True
            page.update()

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

    # Pre-carga estática
    _build_rows(None)   # None → no llama page.update(), solo arma la lista

    return ft.Column(
        controls=[
            form_container,
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            table_container,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN REPORTES (extraída de reportes_view.py)
# ══════════════════════════════════════════════════════════════════════════════

def _build_reportes_tab(
    on_export_csv: Optional[Callable[[], None]] = None,
    on_export_finance_csv: Optional[Callable[[], None]] = None
) -> ft.Control:
    """Construye el contenido completo de la sub-pestaña de Reportes."""

    _bg     = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _fbg    = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _fbrd   = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)

    def _date_tf(hint) -> ft.TextField:
        return ft.TextField(
            hint_text=hint, prefix_icon=ft.Icons.CALENDAR_TODAY_ROUNDED,
            border_radius=10, bgcolor=_fbg, border_color=_fbrd,
            focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
            width=210, height=44,
            content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
            read_only=True,
        )

    date_from = _date_tf("Desde (DD/MM/AAAA)")
    date_to   = _date_tf("Hasta (DD/MM/AAAA)")

    dp_from = ft.DatePicker(
        on_change=lambda e: (
            setattr(date_from, 'value', e.control.value.strftime("%d/%m/%Y") if e.control.value else date_from.value),
            date_from.update()
        )
    )
    dp_to = ft.DatePicker(
        on_change=lambda e: (
            setattr(date_to, 'value', e.control.value.strftime("%d/%m/%Y") if e.control.value else date_to.value),
            date_to.update()
        )
    )

    def open_dp_from(e):
        if dp_from not in e.page.overlay:
            e.page.overlay.append(dp_from)
        dp_from.open = True
        e.page.update()

    def open_dp_to(e):
        if dp_to not in e.page.overlay:
            e.page.overlay.append(dp_to)
        dp_to.open = True
        e.page.update()

    date_from.on_click = open_dp_from
    date_to.on_click = open_dp_to

    tipo_historial = ft.Dropdown(
        options=[
            ft.dropdown.Option("Ingreso de personas"),
            ft.dropdown.Option("Historial de pagos"),
        ],
        value="Ingreso de personas",
        border_radius=10,
        bgcolor=_fbg,
        border_color=_fbrd,
        focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE,
        height=44,
        width=210,
        content_padding=ft.Padding(left=12, top=0, right=12, bottom=0)
    )

    empty_state = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.HISTORY_ROUNDED, size=56, color=ft.Colors.WHITE24),
                ft.Text("Selecciona un rango de fechas y presiona Filtrar",
                        size=14, color=ft.Colors.WHITE38, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        padding=ft.Padding(left=0, top=48, right=0, bottom=48),
        border_radius=14,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
        alignment=ft.Alignment(0, 0),
    )

    historial_container = ft.Container(
        content=empty_state,
        expand=True
    )

    def on_filter(e):
        page = e.page
        df_str = (date_from.value or "").strip()
        dt_str = (date_to.value or "").strip()

        try:
            # Parse DD/MM/AAAA to YYYY-MM-DD
            d_from = datetime.strptime(df_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            d_to = datetime.strptime(dt_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            snack = ft.SnackBar(
                content=ft.Text("Formato de fecha inválido. Usa DD/MM/AAAA.", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.RED_900), duration=3000,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        if tipo_historial.value == "Ingreso de personas":
            datos = obtener_historial_ingresos_rango(d_from, d_to)
            columnas = [
                ft.DataColumn(ft.Text("Fecha / Hora", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Cédula", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Nombre", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
            ]
            filas = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(d["fecha_hora"])),
                    ft.DataCell(ft.Text(d["cedula"])),
                    ft.DataCell(ft.Text(d["nombre"])),
                ]) for d in datos
            ]
        else:
            datos = obtener_historial_pagos_rango(d_from, d_to)
            columnas = [
                ft.DataColumn(ft.Text("Fecha Pago", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Cédula", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Cliente", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Plan", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
                ft.DataColumn(ft.Text("Valor", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
            ]
            filas = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(d["fecha_inicio"])),
                    ft.DataCell(ft.Text(d["cedula"])),
                    ft.DataCell(ft.Text(d["cliente_nombre"])),
                    ft.DataCell(ft.Text(d["plan_nombre"])),
                    ft.DataCell(ft.Text(f'${d["precio"]:,.2f}', color=ft.Colors.GREEN_300)),
                ]) for d in datos
            ]

        if not filas:
            historial_container.content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=56, color=ft.Colors.WHITE24),
                        ft.Text("No se encontraron resultados para esas fechas.",
                                size=14, color=ft.Colors.WHITE38, text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=ft.Padding(left=0, top=48, right=0, bottom=48),
                border_radius=14,
                bgcolor=_bg,
                border=ft.Border(
                    top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
                    bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
                ),
                alignment=ft.Alignment(0, 0),
            )
        else:
            historial_container.content = ft.Container(
                content=ft.DataTable(
                    columns=columnas,
                    rows=filas,
                    heading_row_color=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                    border_radius=12,
                    data_row_max_height=60,
                    expand=True,
                ),
                padding=ft.Padding(left=20, top=20, right=20, bottom=20),
                border_radius=16,
                bgcolor=_bg,
                border=ft.Border(
                    top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
                    bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
                ),
                expand=True
            )
        page.update()

    def _on_export_click(e):
        """Lanza el FilePicker de exportación inyectado desde main.py."""
        if on_export_csv:
            on_export_csv()
        else:
            # Fallback: informar que no hay callback configurado
            snack = ft.SnackBar(
                content=ft.Text("⚠️  Exportación no configurada.", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.ORANGE_900), duration=3000,
            )
            e.page.overlay.append(snack)
            snack.open = True
            e.page.update()

    def _on_export_finance_click(e):
        """Lanza el FilePicker de exportación financiera inyectado desde main.py."""
        if on_export_finance_csv:
            on_export_finance_csv()
        else:
            snack = ft.SnackBar(
                content=ft.Text("⚠️  Exportación financiera no configurada.", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.ORANGE_900), duration=3000,
            )
            e.page.overlay.append(snack)
            snack.open = True
            e.page.update()

    filter_btn = ft.Button(
        "Filtrar",
        icon=ft.Icons.FILTER_LIST_ROUNDED,
        on_click=on_filter,
        bgcolor=ft.Colors.CYAN_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    export_btn = ft.Button(
        "Exportar a Excel (CSV)",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        on_click=_on_export_click,
        style=ft.ButtonStyle(
            color=ft.Colors.GREEN_300,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.GREEN_400),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.40, ft.Colors.GREEN_400)),
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    export_finance_btn = ft.Button(
        "Exportar Reporte Financiero (CSV)",
        icon=ft.Icons.ATTACH_MONEY_ROUNDED,
        on_click=_on_export_finance_click,
        style=ft.ButtonStyle(
            color=ft.Colors.BLUE_300,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.BLUE_400),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.40, ft.Colors.BLUE_400)),
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    filter_row = ft.Row(
        controls=[date_from, date_to, tipo_historial, filter_btn],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    
    export_row = ft.Row(
        controls=[export_btn, export_finance_btn],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    def _summary_card(icon_data, label: str, value: str, color) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(icon_data, size=24, color=color),
                        width=44, height=44,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.1, color),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(value, size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(label, size=11, color=ft.Colors.WHITE38),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.START,
                spacing=6,
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

    aperturas = obtener_aperturas_manuales(50)
    today_str = datetime.now().strftime("%Y-%m-%d")
    hoy_count = sum(1 for a in aperturas if a["fecha_hora"].startswith(today_str))
    resumen   = obtener_resumen_estadisticas()

    summary_row = ft.Row(
        controls=[
            _summary_card(ft.Icons.LOGIN_ROUNDED,      "Ingresos hoy",       str(resumen["ingresos_hoy"]),             ft.Colors.CYAN_400),
            _summary_card(ft.Icons.PAYMENTS_ROUNDED,   "Recaudación hoy",    f"${resumen['recaudacion_hoy']:,.2f}",    ft.Colors.GREEN_400),
            _summary_card(ft.Icons.PEOPLE_ALT_ROUNDED, "Clientes activos",   str(resumen["clientes_activos"]),         ft.Colors.AMBER_400),
            _summary_card(ft.Icons.LOCK_OPEN_ROUNDED,  "Aperturas Manuales", str(hoy_count),                          ft.Colors.ORANGE_400),
        ],
        spacing=14,
    )

    _tbl_header_bg = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    tabla_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(a["fecha_hora"])),
            ft.DataCell(ft.Text(a["justificacion"])),
        ])
        for a in aperturas
    ]

    manual_opens_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha / Hora",  weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
            ft.DataColumn(ft.Text("Justificación", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
        ],
        rows=tabla_rows,
        heading_row_color=_tbl_header_bg,
        border_radius=12,
        data_row_max_height=60,
        expand=True,
    )

    table_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, size=20, color=ft.Colors.ORANGE_400),
                        ft.Text("Registro de Aperturas Manuales", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
                ft.Row(controls=[manual_opens_table], expand=True),
            ],
            expand=True,
        ),
        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
        border_radius=16,
        bgcolor=_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
            bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
        ),
        expand=True,
    )

    return ft.Column(
        controls=[
            summary_row,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            table_container,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Historial detallado", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            filter_row,
            ft.Divider(height=14, color=ft.Colors.TRANSPARENT),
            historial_container,
            ft.Divider(height=14, color=ft.Colors.TRANSPARENT),
            ft.Text("Exportar Historial Completo", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            export_row,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


def _build_auditoria_tab(on_export_audit_csv: Optional[Callable[[], None]]) -> ft.Control:
    from database.db_manager import obtener_historial_congelaciones
    
    _fbg = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _fbrd = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _bg = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _hdr_bg = ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
    
    tabla_auditoria = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Cédula", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Cliente", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Acción", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Justificación", size=12, color=ft.Colors.WHITE38, weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=_hdr_bg,
        border_radius=12,
        data_row_max_height=52,
        expand=True,
    )
    
    table_body = ft.Column(expand=True)
    
    def _build_rows():
        historial = obtener_historial_congelaciones()
        filas = []
        for h in historial:
            accion_color = ft.Colors.ORANGE_400 if h["accion"] == "CONGELADA" else ft.Colors.GREEN_400
            filas.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(h["fecha"], color=ft.Colors.WHITE70)),
                    ft.DataCell(ft.Text(h["cedula"], color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text(h["cliente_nombre"], color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(h["accion"], size=10, weight=ft.FontWeight.BOLD, color=accion_color),
                            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                            border_radius=6,
                            bgcolor=ft.Colors.with_opacity(0.12, accion_color)
                        )
                    ),
                    ft.DataCell(ft.Text(h["justificacion"] or "N/A", color=ft.Colors.WHITE70)),
                ])
            )
        tabla_auditoria.rows = filas
        if filas:
            table_body.controls = [tabla_auditoria]
        else:
            table_body.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SECURITY_ROUNDED, size=52, color=ft.Colors.WHITE24),
                            ft.Text("No hay registros de auditoría.", size=14, color=ft.Colors.WHITE38,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                    ),
                    padding=ft.Padding(left=0, top=40, right=0, bottom=40),
                    alignment=ft.Alignment(0, 0),
                )
            ]
            
    _build_rows() # Cargar datos iniciales
    
    export_btn = ft.ElevatedButton(
        "Exportar Auditoría (CSV)",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.GREEN_700,
        on_click=lambda _: on_export_audit_csv() if on_export_audit_csv else None,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=10),
        )
    )
    
    return ft.Column(
        controls=[
            ft.Row([
                ft.Icon(ft.Icons.SECURITY_ROUNDED, color=ft.Colors.CYAN_400, size=24),
                ft.Text("Auditoría de Congelamientos", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ]),
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("Historial de acciones", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54), export_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    table_body
                ], expand=True),
                padding=ft.Padding(left=20, top=18, right=20, bottom=18),
                border_radius=14,
                bgcolor=_bg,
                border=ft.Border(
                    top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
                    bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
                ),
                expand=True
            )
        ],
        expand=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL — AdminView
# ══════════════════════════════════════════════════════════════════════════════

def AdminView(
    on_export_csv: Optional[Callable[[], None]] = None,
    on_export_finance_csv: Optional[Callable[[], None]] = None,
    on_export_audit_csv: Optional[Callable[[], None]] = None
) -> ft.Control:
    """
    Vista unificada de Administración con dos sub-pestañas: Planes y Reportes.

    Args:
        on_export_csv: Callback sin argumentos que abre el FilePicker de
                       exportación de accesos.
        on_export_finance_csv: Callback sin argumentos que abre el FilePicker de
                               exportación financiera.

    Returns:
        ft.Control: Árbol de widgets de la vista Admin.
    """

    # ── Pre-construimos ambos paneles ──────────────────────────────
    planes_panel   = _build_planes_tab()
    reportes_panel = _build_reportes_tab(
        on_export_csv=on_export_csv,
        on_export_finance_csv=on_export_finance_csv
    )
    auditoria_panel = _build_auditoria_tab(on_export_audit_csv=on_export_audit_csv)

    # ── Contenedor de contenido dinámico ───────────────────────────
    content_host = ft.Container(
        content=planes_panel,
        expand=True,
        padding=ft.Padding(left=0, top=20, right=0, bottom=0),
    )

    # ── Estilos de botones de tab ──────────────────────────────────
    _active_bg   = ft.Colors.with_opacity(0.15, ft.Colors.CYAN_400)
    _active_brd  = ft.Colors.with_opacity(0.50, ft.Colors.CYAN_400)
    _active_col  = ft.Colors.CYAN_300
    _inactive_bg  = ft.Colors.with_opacity(0.04, ft.Colors.WHITE)
    _inactive_brd = ft.Colors.with_opacity(0.10, ft.Colors.WHITE)
    _inactive_col = ft.Colors.WHITE54

    def _tab_style(active: bool) -> ft.ButtonStyle:
        bg  = _active_bg   if active else _inactive_bg
        brd = _active_brd  if active else _inactive_brd
        col = _active_col  if active else _inactive_col
        return ft.ButtonStyle(
            color=col,
            bgcolor=bg,
            side=ft.BorderSide(1, brd),
            padding=ft.Padding(left=20, top=10, right=20, bottom=10),
            shape=ft.RoundedRectangleBorder(radius=10),
        )

    planes_btn_ref   = ft.Ref[ft.Button]()
    reportes_btn_ref = ft.Ref[ft.Button]()
    auditoria_btn_ref = ft.Ref[ft.Button]()

    current_tab = [0]  # mutable container para trackear pestaña activa

    def _set_tab(idx: int, page: ft.Page):
        if idx == current_tab[0]:
            return
        current_tab[0] = idx
        if idx == 0:
            content_host.content = planes_panel
            planes_btn_ref.current.style   = _tab_style(active=True)
            reportes_btn_ref.current.style = _tab_style(active=False)
            auditoria_btn_ref.current.style = _tab_style(active=False)
        elif idx == 1:
            content_host.content = reportes_panel
            planes_btn_ref.current.style   = _tab_style(active=False)
            reportes_btn_ref.current.style = _tab_style(active=True)
            auditoria_btn_ref.current.style = _tab_style(active=False)
        else:
            content_host.content = auditoria_panel
            planes_btn_ref.current.style   = _tab_style(active=False)
            reportes_btn_ref.current.style = _tab_style(active=False)
            auditoria_btn_ref.current.style = _tab_style(active=True)
        page.update()

    def on_planes(e):
        _set_tab(0, e.page)

    def on_reportes(e):
        _set_tab(1, e.page)

    def on_auditoria(e):
        _set_tab(2, e.page)

    planes_btn = ft.Button(
        "Planes",
        ref=planes_btn_ref,
        icon=ft.Icons.CARD_MEMBERSHIP_ROUNDED,
        on_click=on_planes,
        style=_tab_style(active=True),   # activo por defecto
    )

    reportes_btn = ft.Button(
        "Reportes",
        ref=reportes_btn_ref,
        icon=ft.Icons.BAR_CHART_ROUNDED,
        on_click=on_reportes,
        style=_tab_style(active=False),
    )

    auditoria_btn = ft.Button(
        "Auditoría",
        ref=auditoria_btn_ref,
        icon=ft.Icons.SECURITY_ROUNDED,
        on_click=on_auditoria,
        style=_tab_style(active=False),
    )

    tab_bar = ft.Row(
        controls=[planes_btn, reportes_btn, auditoria_btn],
        spacing=8,
    )

    return ft.Column(
        controls=[
            ft.Text("Administración", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Admin", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
            tab_bar,
            ft.Divider(height=4, color=ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            content_host,
        ],
        expand=True,
    )
