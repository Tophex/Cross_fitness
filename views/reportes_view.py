"""
reportes_view.py — Reportes e Historial del gym.

Puntos de extensión:
  - TODO: DB HOOK     → queries de accesos y caja
  - TODO: EXPORT HOOK → exportar a CSV/PDF

Compatibilidad: Flet 0.86+ (ft.Button, ft.Padding, ft.Border, ft.Alignment)
"""

import flet as ft
from datetime import datetime
from database.db_manager import obtener_aperturas_manuales, obtener_resumen_estadisticas


def ReportesView() -> ft.Control:
    """
    Vista de Reportes. Tarjetas resumen, filtros de fecha y área de historial.
    """

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
        )

    date_from = _date_tf("Desde (DD/MM/AAAA)")
    date_to   = _date_tf("Hasta (DD/MM/AAAA)")

    def on_filter(e):
        """TODO: DB HOOK → filtrar historial entre fechas."""
        pass

    def on_export(e):
        """TODO: EXPORT HOOK → exportar a CSV."""
        pass

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
        "Exportar CSV",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        on_click=on_export,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE54,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    filter_row = ft.Row(
        controls=[date_from, date_to, filter_btn, export_btn],
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

    resumen = obtener_resumen_estadisticas()

    summary_row = ft.Row(
        controls=[
            _summary_card(ft.Icons.LOGIN_ROUNDED,      "Ingresos hoy",     str(resumen["ingresos_hoy"]), ft.Colors.CYAN_400),
            _summary_card(ft.Icons.PAYMENTS_ROUNDED,   "Recaudación hoy",  f"${resumen['recaudacion_hoy']:,.2f}", ft.Colors.GREEN_400),
            _summary_card(ft.Icons.PEOPLE_ALT_ROUNDED, "Clientes activos", str(resumen["clientes_activos"]), ft.Colors.AMBER_400),
            _summary_card(ft.Icons.LOCK_OPEN_ROUNDED,  "Aperturas Manuales", str(hoy_count), ft.Colors.ORANGE_400),
        ],
        spacing=14,
    )

    _tbl_header_bg = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    tabla_rows = []
    for a in aperturas:
        tabla_rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(a["fecha_hora"])),
                ft.DataCell(ft.Text(a["justificacion"])),
            ])
        )

    manual_opens_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha / Hora", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)),
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

    return ft.Column(
        controls=[
            ft.Text("Estadísticas y Rendimiento", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Reportes y Estadísticas", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            summary_row,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            table_container,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Historial detallado", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            filter_row,
            ft.Divider(height=14, color=ft.Colors.TRANSPARENT),
            empty_state,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
