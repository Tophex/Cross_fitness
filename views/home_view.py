"""
home_view.py
------------
Vista principal (Dashboard) de la aplicación.
Muestra el estado del lector biométrico y servirá como hub central
para el control de acceso. En el futuro, este módulo conectará con
la lógica del lector de huellas (hardware/SDK).

Compatibilidad: Flet 0.86+
  - ft.Icon(IconData, ...)         → primer arg posicional
  - ft.Padding(left, top, right, bottom) → en vez de ft.padding.symmetric/only
  - ft.Border(top, right, bottom, left)  → en vez de ft.border.all/only
"""

import flet as ft


def HomeView() -> ft.Control:
    """
    Construye y retorna el widget de la vista de Inicio.

    Retorna un control de Flet listo para insertarse en el contenedor
    dinámico de main.py. Para conectar el lector biométrico, busca
    el comentario # TODO: BIOMETRIC HOOK.

    Returns:
        ft.Control: El árbol de widgets de la vista de Inicio.
    """

    # ── Indicador de estado del sensor ────────────────────────────
    # TODO: BIOMETRIC HOOK → sustituir por lógica real del SDK
    status_icon = ft.Icon(
        ft.Icons.FINGERPRINT,       # Flet 0.86+: primer arg posicional
        size=120,
        color=ft.Colors.CYAN_400,
    )

    status_text = ft.Text(
        value="Esperando Huella...",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE,
        text_align=ft.TextAlign.CENTER,
    )

    subtitle_text = ft.Text(
        value="Apoya tu dedo en el lector para registrar el acceso.",
        size=14,
        color=ft.Colors.WHITE54,
        text_align=ft.TextAlign.CENTER,
    )

    # ── Tarjeta central destacada ──────────────────────────────────
    _white12 = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _cyan_glow = ft.Colors.with_opacity(0.18, ft.Colors.CYAN_400)
    _card_bg  = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)

    biometric_card = ft.Container(
        content=ft.Column(
            controls=[
                status_icon,
                ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
                status_text,
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                subtitle_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
        width=480,
        padding=ft.Padding(left=40, top=60, right=40, bottom=60),
        border_radius=24,
        bgcolor=_card_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _white12),
            right=ft.BorderSide(1, _white12),
            bottom=ft.BorderSide(1, _white12),
            left=ft.BorderSide(1, _white12),
        ),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=40,
            color=_cyan_glow,
            offset=ft.Offset(0, 0),
        ),
    )

    # ── Fila de estadísticas rápidas (placeholder) ─────────────────
    def _stat_chip(icon_data, label: str, value: str) -> ft.Container:
        """Genera una pequeña tarjeta de estadística para el dashboard."""
        _chip_bg    = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
        _chip_border = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(icon_data, size=28, color=ft.Colors.CYAN_400),
                    ft.Text(value, size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(label, size=11, color=ft.Colors.WHITE54),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding(left=28, top=20, right=28, bottom=20),
            border_radius=16,
            bgcolor=_chip_bg,
            border=ft.Border(
                top=ft.BorderSide(1, _chip_border),
                right=ft.BorderSide(1, _chip_border),
                bottom=ft.BorderSide(1, _chip_border),
                left=ft.BorderSide(1, _chip_border),
            ),
        )

    stats_row = ft.Row(
        controls=[
            _stat_chip(ft.Icons.PEOPLE_ALT_ROUNDED, "Usuarios activos", "—"),
            _stat_chip(ft.Icons.LOGIN_ROUNDED,       "Ingresos hoy",    "—"),
            _stat_chip(ft.Icons.LOGOUT_ROUNDED,      "Salidas hoy",     "—"),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
    )

    # ── Ensamblado final de la vista ───────────────────────────────
    return ft.Column(
        controls=[
            ft.Text(
                "Dashboard",
                size=13,
                color=ft.Colors.WHITE38,
                weight=ft.FontWeight.W_500,
            ),
            ft.Text(
                "Control de Acceso",
                size=26,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            ),
            ft.Divider(height=32, color=ft.Colors.TRANSPARENT),
            biometric_card,
            ft.Divider(height=32, color=ft.Colors.TRANSPARENT),
            stats_row,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
    )
