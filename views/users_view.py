"""
users_view.py — Vista de gestión de Usuarios.
Placeholder listo para conectar con la base de datos de miembros del gym.
"""

import flet as ft


def UsersView() -> ft.Control:
    """
    Construye y retorna el widget de la vista de Usuarios.
    Conectar con SQLite/API REST en el futuro para CRUD de miembros.
    """
    _bg     = ft.Colors.with_opacity(0.04, ft.Colors.WHITE)
    _border = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
    return ft.Column(
        controls=[
            ft.Text("Gestión", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Usuarios", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=32, color=ft.Colors.TRANSPARENT),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED, size=64, color=ft.Colors.WHITE24),
                        ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            "Módulo de usuarios en construcción",
                            size=18, color=ft.Colors.WHITE54,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Aquí podrás registrar, editar y dar de baja a los miembros del gym.",
                            size=13, color=ft.Colors.WHITE38,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                padding=ft.Padding(left=60, top=60, right=60, bottom=60),
                border_radius=20,
                bgcolor=_bg,
                border=ft.Border(
                    top=ft.BorderSide(1, _border), right=ft.BorderSide(1, _border),
                    bottom=ft.BorderSide(1, _border), left=ft.BorderSide(1, _border),
                ),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
    )
