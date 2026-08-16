"""
config_view.py — Configuración del sistema (puertos COM, datos del gym).

Funcionalidad implementada (Fase 5b):
  - Sección Hardware: TextField para el puerto COM del torniquete.
  - Botón 'Guardar Configuración' → persiste en tabla `configuracion` de la BD.
  - Botón 'Probar Apertura'       → llama a TorniqueteController.abrir_torniquete()
                                     y muestra SnackBar verde (éxito) o rojo (error).

Compatibilidad: Flet 0.86+ (ft.Button, ft.Padding, ft.Border)
"""

import threading
import flet as ft

from database.db_manager import get_config, set_config
from hardware.serial_manager import TorniqueteController


def ConfigView() -> ft.Control:
    """
    Vista de Configuración. Puertos COM del hardware y datos del gimnasio.
    """

    _bg     = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
    _brd    = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    _fbg    = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    _dd_bg  = "#1C1D22"
    _fbrd   = ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
    _divbrd = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)

    # ── Helpers visuales ───────────────────────────────────────────────────────
    def _section(title: str, icon_data, controls: list) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon_data, size=18, color=ft.Colors.CYAN_400),
                            ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=12, color=_divbrd),
                    *controls,
                ],
                spacing=10,
            ),
            padding=ft.Padding(left=20, top=18, right=20, bottom=18),
            border_radius=14,
            bgcolor=_bg,
            border=ft.Border(
                top=ft.BorderSide(1, _brd), right=ft.BorderSide(1, _brd),
                bottom=ft.BorderSide(1, _brd), left=ft.BorderSide(1, _brd),
            ),
        )

    def _labeled_tf(label: str, hint: str, value: str = "", width=None) -> ft.Column:
        tf = ft.TextField(
            value=value, hint_text=hint,
            border_radius=10, bgcolor=_fbg, border_color=_fbrd,
            focused_border_color=ft.Colors.CYAN_400, color=ft.Colors.WHITE,
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38),
            height=44,
            content_padding=ft.Padding(left=12, top=0, right=12, bottom=0),
            **({} if width is None else {"width": width}),
            **({} if width is not None else {"expand": True}),
        )
        col = ft.Column(
            controls=[ft.Text(label, size=11, color=ft.Colors.WHITE54), tf],
            spacing=4,
            **({} if width is not None else {"expand": True}),
        )
        col._tf_ref = tf  # guardar referencia interna al campo
        return col

    # ── Sección Hardware / Puerto COM ──────────────────────────────────────────
    # Carga el valor guardado en la BD (vacío si es la primera vez)
    _puerto_guardado = get_config("puerto_com_torniquete", "")

    com_col = _labeled_tf(
        "Puerto COM del Torniquete",
        "Ej. COM3 o /dev/ttyUSB0",
        value=_puerto_guardado,
    )
    com_tf: ft.TextField = com_col._tf_ref  # acceso directo al TextField

    # Estado visual del botón de prueba
    test_btn_ref = ft.Ref[ft.Button]()

    def _show_snack(page: ft.Page, mensaje: str, ok: bool) -> None:
        """Muestra un SnackBar verde (ok) o rojo (error)."""
        color_bg = ft.Colors.with_opacity(0.92, ft.Colors.GREEN_900) if ok \
                   else ft.Colors.with_opacity(0.92, ft.Colors.RED_900)
        icon    = "✅" if ok else "❌"
        snack = ft.SnackBar(
            content=ft.Text(f"{icon}  {mensaje}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=color_bg,
            duration=4000,
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def on_test(e: ft.ControlEvent) -> None:
        """Prueba la conexión serial con el puerto COM guardado."""
        page = e.page
        puerto = com_tf.value.strip() if com_tf.value else ""

        if not puerto:
            _show_snack(page, "Primero ingresa y guarda el puerto COM.", ok=False)
            return

        # Deshabilitar botón mientras se prueba
        btn = test_btn_ref.current
        btn.disabled = True
        btn.text = "Probando…"
        page.update()

        def _run_test():
            ctrl = TorniqueteController()
            ok, msg = ctrl.abrir_torniquete(puerto)

            # Volver al hilo de UI
            def _update(_=None):
                btn.disabled = False
                btn.text = "Probar Apertura"
                if ok:
                    _show_snack(page, f"Torniquete abierto correctamente en {puerto}.", ok=True)
                else:
                    _show_snack(page, f"Error de hardware → {msg}", ok=False)
                page.update()

            # Programar el update en el event loop de Flet
            page.run_thread(_update) if hasattr(page, "run_thread") else _update()

        threading.Thread(target=_run_test, daemon=True).start()

    def on_save(e: ft.ControlEvent) -> None:
        """Guarda el puerto COM y los datos del gimnasio en la BD."""
        page = e.page
        puerto = com_tf.value.strip() if com_tf.value else ""

        if puerto:
            puerto_upper = puerto.upper()
            com_tf.value = puerto_upper
            set_config("puerto_com_torniquete", puerto_upper)

        # Guardar datos del gym
        if gym_nombre_tf:
            set_config("gym_nombre",    gym_nombre_tf.value or "")
        if gym_telefono_tf:
            set_config("gym_telefono",  gym_telefono_tf.value or "")
        if gym_direccion_tf:
            set_config("gym_direccion", gym_direccion_tf.value or "")

        _show_snack(page, "Configuración guardada correctamente.", ok=True)

    test_btn = ft.Button(
        "Probar Apertura",
        ref=test_btn_ref,
        icon=ft.Icons.CABLE_ROUNDED,
        on_click=on_test,
        style=ft.ButtonStyle(
            color=ft.Colors.CYAN_400,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.CYAN_400),
            side=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.CYAN_400)),
            padding=ft.Padding(left=18, top=10, right=18, bottom=10),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    com_section = _section("Hardware / Puerto COM del Torniquete", ft.Icons.USB_ROUNDED, [
        ft.Row(controls=[com_col], spacing=12),
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=13, color=ft.Colors.WHITE38),
                    ft.Text(
                        "Ingresa el nombre del puerto al que está conectado el microcontrolador "
                        "(Arduino / ESP32). En Windows: COM3, COM4… En Linux: /dev/ttyUSB0",
                        size=11, color=ft.Colors.WHITE38,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.Padding(left=4, top=0, right=0, bottom=0),
        ),
        ft.Row(controls=[test_btn], alignment=ft.MainAxisAlignment.END),
    ])

    # ── Sección Datos del Gym ──────────────────────────────────────────────────
    gym_nombre_col    = _labeled_tf("Nombre del gym",  "Ej. GymPro Total Fitness",
                                     value=get_config("gym_nombre",    ""))
    gym_telefono_col  = _labeled_tf("Teléfono",        "Ej. 555-1234",
                                     value=get_config("gym_telefono",  ""), width=170)
    gym_direccion_col = _labeled_tf("Dirección",       "Calle, número, colonia…",
                                     value=get_config("gym_direccion", ""))

    # Referencias directas a los TextFields para leerlos en on_save
    gym_nombre_tf:    ft.TextField = gym_nombre_col._tf_ref
    gym_telefono_tf:  ft.TextField = gym_telefono_col._tf_ref
    gym_direccion_tf: ft.TextField = gym_direccion_col._tf_ref

    gym_section = _section("Datos del Gimnasio", ft.Icons.FITNESS_CENTER_ROUNDED, [
        ft.Row(controls=[gym_nombre_col, gym_telefono_col], spacing=12),
        gym_direccion_col,
    ])

    # ── Botón principal Guardar ────────────────────────────────────────────────
    save_btn = ft.Button(
        "Guardar Configuración",
        icon=ft.Icons.SAVE_ROUNDED,
        on_click=on_save,
        bgcolor=ft.Colors.CYAN_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            padding=ft.Padding(left=28, top=14, right=28, bottom=14),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    return ft.Column(
        controls=[
            ft.Text("Sistema", size=13, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_500),
            ft.Text("Configuración", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            com_section,
            ft.Divider(height=14, color=ft.Colors.TRANSPARENT),
            gym_section,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Row(controls=[save_btn], alignment=ft.MainAxisAlignment.END),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
