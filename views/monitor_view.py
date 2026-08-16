"""
monitor_view.py — Vista principal del control de acceso en tiempo real.

La función MonitorView() acepta un parámetro opcional `require_auth`:
  - Si se pasa, el botón 'Apertura Manual' solicita contraseña antes de actuar.
  - Si no se pasa (None), el botón actúa directamente (útil para pruebas).

Puntos de extensión:
  - TODO: BIOMETRIC HOOK → conectar SDK del lector en la lógica de huella
  - TODO: RELAY HOOK     → enviar señal real al relé dentro de _do_open()

Compatibilidad: Flet 0.86+ (ft.Button, ft.Padding, ft.Border, ft.Alignment)
"""

import flet as ft
from typing import Callable, Optional
import asyncio
import threading

from database.db_manager import verificar_estado_acceso, registrar_apertura_manual, get_config
from hardware.serial_manager import TorniqueteController


def MonitorView(
    require_auth: Optional[Callable[[ft.Page, Callable, str], None]] = None
) -> ft.Control:
    """
    Vista del Monitor de acceso en tiempo real.

    Args:
        require_auth: Función de autenticación inyectada desde main.py.
                      Firma esperada: require_auth(page, on_success, context_label)
                      Si es None, el botón 'Apertura Manual' actúa sin pedir clave.

    Returns:
        ft.Control: Árbol de widgets de la vista Monitor.
    """

    # ── Estado biométrico central ──────────────────────────────────
    fingerprint_icon = ft.Icon(ft.Icons.FINGERPRINT, size=110, color=ft.Colors.WHITE54)

    status_label = ft.Text(
        "Esperando lectura...",
        size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE,
        text_align=ft.TextAlign.CENTER,
    )
    status_sub = ft.Text(
        "Ingresa una cédula para simular la huella",
        size=13, color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER,
    )

    # ── Botón de Apertura Manual (protegido con contraseña) ────────
    manual_btn_ref = ft.Ref[ft.Button]()   # referencia para modificarlo post-creación

    # ── Diálogo Custom de Apertura Manual ──────────────────────────
    pwd_field = ft.TextField(
        hint_text="Contraseña de administrador", password=True, can_reveal_password=True,
        border_radius=10, bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE, hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED, height=48,
        content_padding=ft.Padding(left=14, top=0, right=14, bottom=0),
    )

    reason_field = ft.TextField(
        hint_text="Justificación (ej. Llegó un pedido)", multiline=True, min_lines=2, max_lines=3,
        border_radius=10, bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE, hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
        prefix_icon=ft.Icons.EDIT_NOTE_ROUNDED,
        content_padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    error_label = ft.Text("", size=12, color=ft.Colors.RED_400, visible=False)

    def _close_custom_dialog(e=None):
        custom_dialog.open = False
        pwd_field.value = ""
        reason_field.value = ""
        error_label.visible = False
        pwd_field.border_color = ft.Colors.with_opacity(0.15, ft.Colors.WHITE)
        reason_field.border_color = ft.Colors.with_opacity(0.15, ft.Colors.WHITE)
        manual_btn_ref.current.page.update()

    def _submit_custom_dialog(e):
        page = e.control.page
        pwd = pwd_field.value or ""
        reason = (reason_field.value or "").strip()

        # Validación
        has_error = False
        if pwd != "admin123":
            pwd_field.border_color = ft.Colors.RED_400
            has_error = True
        else:
            pwd_field.border_color = ft.Colors.with_opacity(0.15, ft.Colors.WHITE)

        if not reason:
            reason_field.border_color = ft.Colors.RED_400
            has_error = True
        else:
            reason_field.border_color = ft.Colors.with_opacity(0.15, ft.Colors.WHITE)

        if has_error:
            error_label.value = "Contraseña incorrecta o justificación vacía."
            error_label.visible = True
            page.update()
            return

        # Éxito
        registrar_apertura_manual(reason)
        _close_custom_dialog()

        # Feedback visual en el botón
        manual_btn_ref.current.content = ft.Text(
            "¡Torniquete abierto!", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14,
        )
        manual_btn_ref.current.bgcolor = ft.Colors.GREEN_700
        manual_btn_ref.current.style = ft.ButtonStyle(
            padding=ft.Padding(left=32, top=16, right=32, bottom=16),
            shape=ft.RoundedRectangleBorder(radius=12),
        )

        snack = ft.SnackBar(
            content=ft.Text("✅  Torniquete abierto. Razón guardada.", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.GREEN_900), duration=3000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

        # ── Señal al hardware en segundo plano ──────────────────────
        def _send_manual_signal():
            puerto = get_config("puerto_com_torniquete", "")
            ctrl = TorniqueteController()
            ok, msg = ctrl.abrir_torniquete(puerto)
            if not ok:
                def _show_hw_error(_=None):
                    err_snack = ft.SnackBar(
                        content=ft.Text(
                            f"⚠️  Hardware no respondió: {msg}",
                            color=ft.Colors.WHITE, weight=ft.FontWeight.W_500,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900),
                        duration=5000,
                    )
                    page.overlay.append(err_snack)
                    err_snack.open = True
                    page.update()
                page.run_thread(_show_hw_error) if hasattr(page, "run_thread") else _show_hw_error()

        threading.Thread(target=_send_manual_signal, daemon=True).start()

    custom_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.LOCK_OPEN_ROUNDED, color=ft.Colors.ORANGE_400, size=22),
                    width=36, height=36, border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.ORANGE_400), alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Apertura Manual", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("Se requiere contraseña y justificación.", size=11, color=ft.Colors.WHITE54),
                    ], spacing=1,
                ),
            ], spacing=10,
        ),
        content=ft.Column(
            controls=[
                ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                pwd_field,
                reason_field,
                error_label,
            ], spacing=10, width=340, tight=True,
        ),
        actions=[
            ft.Button(
                "Cancelar", on_click=_close_custom_dialog,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE54, bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                    padding=ft.Padding(left=18, top=10, right=18, bottom=10), shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
            ft.Button(
                "Aceptar", icon=ft.Icons.CHECK_CIRCLE_ROUNDED, on_click=_submit_custom_dialog,
                bgcolor=ft.Colors.CYAN_700, color=ft.Colors.WHITE,
                style=ft.ButtonStyle(
                    padding=ft.Padding(left=18, top=10, right=18, bottom=10), shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor="#1A1D24", shape=ft.RoundedRectangleBorder(radius=18),
    )

    def on_manual_click(e: ft.ControlEvent) -> None:
        """Abre el diálogo customizado de apertura."""
        page = e.page
        if custom_dialog not in page.overlay:
            page.overlay.append(custom_dialog)
        custom_dialog.open = True
        pwd_field.focus()
        page.update()

    _card_bg     = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _card_border = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _glow        = ft.Colors.with_opacity(0.15, ft.Colors.CYAN_400)

    manual_btn = ft.Button(
        "Apertura Manual",
        ref=manual_btn_ref,
        icon=ft.Icons.LOCK_OPEN_ROUNDED,
        on_click=on_manual_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.CYAN_400),
            color=ft.Colors.CYAN_200,
            padding=ft.Padding(left=32, top=16, right=32, bottom=16),
            shape=ft.RoundedRectangleBorder(radius=12),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.CYAN_400)),
        ),
    )

    # ── Simulación Biométrica ──────────────────────────────────────
    sim_cedula_tf = ft.TextField(
        hint_text="Cédula a simular",
        border_radius=10, bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), focused_border_color=ft.Colors.CYAN_400,
        color=ft.Colors.WHITE, height=44,
        prefix_icon=ft.Icons.BADGE_ROUNDED,
        expand=True,
    )

    async def _reset_ui(delay=3.5):
        await asyncio.sleep(delay)
        # Regresar al estado gris
        fingerprint_icon.name = ft.Icons.FINGERPRINT
        fingerprint_icon.color = ft.Colors.WHITE54
        status_label.value = "Esperando lectura..."
        status_sub.value = "Ingresa una cédula para simular la huella"
        biometric_card.bgcolor = _card_bg
        biometric_card.shadow.color = _glow
        biometric_card.border = ft.Border(
            top=ft.BorderSide(1, _card_border), right=ft.BorderSide(1, _card_border),
            bottom=ft.BorderSide(1, _card_border), left=ft.BorderSide(1, _card_border),
        )
        sim_cedula_tf.value = ""
        try:
            biometric_card.update()
        except Exception:
            pass

    def on_simulate(e):
        cedula = sim_cedula_tf.value.strip()
        if not cedula:
            return

        res = verificar_estado_acceso(cedula)

        if res["permitido"]:
            fingerprint_icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED
            fingerprint_icon.color = ft.Colors.GREEN_400
            status_label.value = "ACCESO PERMITIDO"
            status_sub.value = f"{res['cliente_nombre']} - Quedan {res['dias_restantes']} días"

            biometric_card.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREEN_400)
            biometric_card.shadow.color = ft.Colors.with_opacity(0.2, ft.Colors.GREEN_400)
            biometric_card.border = ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREEN_500), right=ft.BorderSide(1, ft.Colors.GREEN_500),
                bottom=ft.BorderSide(1, ft.Colors.GREEN_500), left=ft.BorderSide(1, ft.Colors.GREEN_500),
            )

            # ── Señal al hardware en segundo plano ──────────────────
            _page = e.page
            def _send_biometric_signal():
                puerto = get_config("puerto_com_torniquete", "")
                ctrl = TorniqueteController()
                ok, msg = ctrl.abrir_torniquete(puerto)
                if not ok:
                    def _show_hw_error(_=None):
                        err_snack = ft.SnackBar(
                            content=ft.Text(
                                f"⚠️  Hardware no respondió: {msg}",
                                color=ft.Colors.WHITE, weight=ft.FontWeight.W_500,
                            ),
                            bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900),
                            duration=5000,
                        )
                        _page.overlay.append(err_snack)
                        err_snack.open = True
                        _page.update()
                    _page.run_thread(_show_hw_error) if hasattr(_page, "run_thread") else _show_hw_error()

            threading.Thread(target=_send_biometric_signal, daemon=True).start()

        else:
            fingerprint_icon.name = ft.Icons.CANCEL_ROUNDED
            fingerprint_icon.color = ft.Colors.RED_400
            status_label.value = "ACCESO DENEGADO"
            status_sub.value = res["mensaje"]

            biometric_card.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.RED_400)
            biometric_card.shadow.color = ft.Colors.with_opacity(0.2, ft.Colors.RED_400)
            biometric_card.border = ft.Border(
                top=ft.BorderSide(1, ft.Colors.RED_500), right=ft.BorderSide(1, ft.Colors.RED_500),
                bottom=ft.BorderSide(1, ft.Colors.RED_500), left=ft.BorderSide(1, ft.Colors.RED_500),
            )

        biometric_card.update()
        e.page.run_task(_reset_ui)

    sim_btn = ft.Button(
        "Simular Lectura",
        on_click=on_simulate,
        bgcolor=ft.Colors.CYAN_700, color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=16, top=10, right=16, bottom=10),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    biometric_card = ft.Container(
        content=ft.Column(
            controls=[
                fingerprint_icon,
                ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                status_label,
                ft.Divider(height=6,  color=ft.Colors.TRANSPARENT),
                status_sub,
                ft.Divider(height=24, color=ft.Colors.TRANSPARENT),
                ft.Row([sim_cedula_tf, sim_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=16, color=ft.Colors.TRANSPARENT),
                manual_btn,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
        width=460,
        padding=ft.Padding(left=40, top=52, right=40, bottom=52),
        border_radius=24,
        bgcolor=_card_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _card_border), right=ft.BorderSide(1, _card_border),
            bottom=ft.BorderSide(1, _card_border), left=ft.BorderSide(1, _card_border),
        ),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=50, color=_glow, offset=ft.Offset(0, 0)),
    )

    # ── Panel de últimos accesos ───────────────────────────────────
    def _access_row(name: str, time: str, status: str, color) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PERSON_ROUNDED, size=20, color=color),
                    ft.Column(
                        controls=[
                            ft.Text(name, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                            ft.Text(time, size=11, color=ft.Colors.WHITE38),
                        ],
                        spacing=1, expand=True,
                    ),
                    ft.Container(
                        content=ft.Text(status, size=10, color=color, weight=ft.FontWeight.BOLD),
                        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                        border_radius=6,
                        bgcolor=ft.Colors.with_opacity(0.12, color),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
        )

    _panel_bg  = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _panel_brd = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)

    recent_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Últimos accesos", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                _access_row("— sin datos —", "--:--", "PENDIENTE", ft.Colors.WHITE24),
            ],
            spacing=6,
        ),
        width=240,
        padding=ft.Padding(left=18, top=18, right=18, bottom=18),
        border_radius=16,
        bgcolor=_panel_bg,
        border=ft.Border(
            top=ft.BorderSide(1, _panel_brd), right=ft.BorderSide(1, _panel_brd),
            bottom=ft.BorderSide(1, _panel_brd), left=ft.BorderSide(1, _panel_brd),
        ),
        expand=True,
    )

    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Monitor", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    # Badge que indica que algunas acciones están protegidas
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SHIELD_ROUNDED, size=12, color=ft.Colors.CYAN_400),
                                ft.Text("Apertura Manual protegida", size=11, color=ft.Colors.CYAN_400),
                            ],
                            spacing=4,
                        ),
                        padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                        border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.CYAN_400),
                    ),
                ],
            ),
            ft.Text("Control de Acceso en Tiempo Real", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=28, color=ft.Colors.TRANSPARENT),
            ft.Row(
                controls=[biometric_card, recent_panel],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=24,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
    )
