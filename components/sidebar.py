"""
sidebar.py
----------
Componente de navegación lateral fijo (Sidebar).

Usa NavigationRail de Material Design con 6 destinos correspondientes
a las secciones del sistema. Emite el índice seleccionado al padre
(main.py) vía el callback on_navigate para el cambio dinámico de vistas.

Índices de navegación (constantes NAV_*):
  0 → Monitor       (acceso en tiempo real)
  1 → Clientes      (gestión de miembros)
  2 → Renovaciones  (pagos y membresías)
  3 → Planes        (catálogo de planes)
  4 → Reportes      (historial y caja)
  5 → Configuración (puertos COM y ajustes)

Compatibilidad: Flet 0.86+
  - ft.Icon(IconData, ...)                → primer arg posicional
  - ft.NavigationRailDestination(IconData)→ primer arg posicional
  - ft.Padding(left, top, right, bottom)  → en vez de ft.padding.only
  - ft.Border(right=ft.BorderSide(...))   → en vez de ft.border.only
  - ft.Alignment(x, y)                   → en vez de ft.alignment.center
  - ft.Text(style=ft.TextStyle(...))      → para letter_spacing
"""

import flet as ft
from typing import Callable


# ── Índices de navegación ─────────────────────────────────────────────────────
NAV_MONITOR      = 0
NAV_CLIENTES     = 1
NAV_RENOVACIONES = 2
NAV_PLANES       = 3
NAV_REPORTES     = 4
NAV_CONFIG       = 5


def Sidebar(on_navigate: Callable[[int], None]) -> ft.Control:
    """
    Construye y retorna el widget del menú lateral de 6 secciones.

    Args:
        on_navigate: Callback invocado con el índice de la opción
                     seleccionada. main.py lo recibe y actualiza
                     el contenedor dinámico con la vista correcta.

    Returns:
        ft.Control: Sidebar completo listo para montar en el layout.
    """

    def _handle_change(e: ft.ControlEvent) -> None:
        """Delega el evento de cambio al callback externo."""
        on_navigate(int(e.data))

    # ── Logo / branding ────────────────────────────────────────────
    leading = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.FITNESS_CENTER_ROUNDED,
                        color=ft.Colors.CYAN_400,
                        size=26,
                    ),
                    width=46,
                    height=46,
                    border_radius=13,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN_400),
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(
                    "GYM",
                    size=9,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.CYAN_400,
                    style=ft.TextStyle(letter_spacing=3),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5,
        ),
        padding=ft.Padding(left=0, top=16, right=0, bottom=4),
    )

    rail = ft.NavigationRail(
        destinations=[
            ft.NavigationRailDestination(
                ft.Icons.MONITOR_HEART_OUTLINED,
                selected_icon=ft.Icons.MONITOR_HEART,
                label="Monitor",
            ),
            ft.NavigationRailDestination(
                ft.Icons.PEOPLE_ALT_OUTLINED,
                selected_icon=ft.Icons.PEOPLE_ALT_ROUNDED,
                label="Clientes",
            ),
            ft.NavigationRailDestination(
                ft.Icons.AUTORENEW_ROUNDED,
                selected_icon=ft.Icons.AUTORENEW_ROUNDED,
                label="Renovac.",
            ),
            ft.NavigationRailDestination(
                ft.Icons.CARD_MEMBERSHIP_OUTLINED,
                selected_icon=ft.Icons.CARD_MEMBERSHIP_ROUNDED,
                label="Planes",
            ),
            ft.NavigationRailDestination(
                ft.Icons.BAR_CHART_OUTLINED,
                selected_icon=ft.Icons.BAR_CHART_ROUNDED,
                label="Reportes",
            ),
            ft.NavigationRailDestination(
                ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS_ROUNDED,
                label="Config.",
            ),
        ],
        selected_index=NAV_MONITOR,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=82,
        min_extended_width=200,
        group_alignment=-0.85,
        on_change=_handle_change,
        bgcolor=ft.Colors.TRANSPARENT,
        indicator_color=ft.Colors.with_opacity(0.13, ft.Colors.CYAN_400),
        indicator_shape=ft.RoundedRectangleBorder(radius=12),
        leading=leading,
    )

    _border_color = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    return ft.Container(
        content=rail,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
        border=ft.Border(right=ft.BorderSide(1, _border_color)),
    )
