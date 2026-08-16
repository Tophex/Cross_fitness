"""
auth_dialog.py
--------------
Componente reutilizable de autenticación por contraseña.

Expone la función show_auth_dialog() que muestra un AlertDialog modal
con un campo de contraseña. Si el usuario ingresa la clave correcta,
ejecuta el callback on_success. Si falla, muestra un SnackBar de error.

Uso:
    from components.auth_dialog import show_auth_dialog

    show_auth_dialog(
        page,
        on_success=lambda: print("¡Autenticado!"),
        context_label="acceder a Reportes",
    )

Nota de seguridad:
    La constante ADMIN_PASSWORD es un placeholder para desarrollo.
    En producción, usar hash bcrypt + almacenamiento seguro.

Compatibilidad: Flet 0.86+
"""

import flet as ft
from typing import Callable

# ── Constante de contraseña (mover a config seguro en producción) ──────────────
ADMIN_PASSWORD = "admin123"


def show_auth_dialog(
    page: ft.Page,
    on_success: Callable[[], None],
    context_label: str = "esta acción",
) -> None:
    """
    Muestra un AlertDialog modal que solicita la contraseña de administrador.

    Flujo:
      1. Se agrega el diálogo a page.overlay y se abre.
      2. Si la contraseña ingresada == ADMIN_PASSWORD → cierra diálogo + llama on_success.
      3. Si es incorrecta → muestra SnackBar de error y limpia el campo.
      4. 'Cancelar' cierra el diálogo sin ejecutar nada.

    Args:
        page: Referencia a la página raíz de Flet.
        on_success: Callback invocado cuando la contraseña es correcta.
        context_label: Texto descriptivo de la acción protegida
                       (ej. "acceder a Reportes").
    """

    # ── Campo de contraseña ────────────────────────────────────────
    pwd_field = ft.TextField(
        hint_text="Contraseña de administrador",
        password=True,
        can_reveal_password=True,
        autofocus=True,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
        focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
        height=48,
        content_padding=ft.Padding(left=14, top=0, right=14, bottom=0),
    )

    # Etiqueta de error (oculta inicialmente)
    error_label = ft.Text(
        "",
        size=12,
        color=ft.Colors.RED_400,
        visible=False,
    )

    # ── Referencia al diálogo (necesaria para cerrarlo desde dentro) ───
    dialog: ft.AlertDialog = None  # se asigna más abajo

    def _close(e=None) -> None:
        """Cierra el diálogo estableciendo open a False."""
        dialog.open = False
        page.update()

    def _submit(e=None) -> None:
        """
        Valida la contraseña ingresada.
        - Correcta → cierra diálogo y ejecuta on_success.
        - Incorrecta → muestra error inline y SnackBar.
        """
        entered = pwd_field.value or ""

        if entered == ADMIN_PASSWORD:
            _close()
            on_success()
        else:
            # Feedback inline
            error_label.value   = "Contraseña incorrecta. Intenta de nuevo."
            error_label.visible = True
            pwd_field.value     = ""
            pwd_field.border_color = ft.Colors.RED_400
            page.update()

            # SnackBar de error adicional
            snack = ft.SnackBar(
                content=ft.Text(
                    "❌  Contraseña incorrecta",
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.W_500,
                ),
                bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900),
                duration=2500,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()

    # Permitir confirmar con Enter en el campo
    pwd_field.on_submit = _submit

    # ── Construcción del diálogo ───────────────────────────────────
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED,
                                    color=ft.Colors.CYAN_400, size=22),
                    width=36, height=36,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN_400),
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Acceso restringido", size=15,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"Se requiere contraseña para {context_label}.",
                                size=11, color=ft.Colors.WHITE54),
                    ],
                    spacing=1,
                ),
            ],
            spacing=10,
        ),
        content=ft.Column(
            controls=[
                ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                pwd_field,
                error_label,
                ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
            ],
            spacing=8,
            width=340,
            tight=True,
        ),
        actions=[
            ft.Button(
                "Cancelar",
                on_click=_close,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE54,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                    padding=ft.Padding(left=18, top=10, right=18, bottom=10),
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
            ft.Button(
                "Aceptar",
                icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                on_click=_submit,
                bgcolor=ft.Colors.CYAN_700,
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(
                    padding=ft.Padding(left=18, top=10, right=18, bottom=10),
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor="#1A1D24",
        shape=ft.RoundedRectangleBorder(radius=18),
    )

    # ── Mostrar diálogo ────────────────────────────────────────────
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
