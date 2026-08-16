"""
main.py
-------
Punto de entrada de la aplicación 'Control de Acceso Gym'.

Responsabilidades:
  1. Configurar la ventana principal (tamaño, tema, título).
  2. Instanciar el sidebar y el contenedor de contenido dinámico.
  3. Orquestar el cambio de vista mediante VIEW_MAP.
  4. Gestionar la seguridad: rutas libres vs. rutas protegidas por contraseña.
  5. (Fase 7) Gestionar el ft.FilePicker para exportación CSV de ingresos.

Flujo de datos:
  Sidebar ──on_navigate(índice)──► navigate(índice)
                                      ├─ ruta libre    → cambia vista directo
                                      └─ ruta protegida → show_auth_dialog()
                                                               └─ on_success → cambia vista

  AdminView ──on_export_csv()──► _open_export_picker()
                                      └─ FilePicker.save_file()
                                              └─ on_picker_result()
                                                      └─ exportar_ingresos_csv(ruta)
                                                      └─ SnackBar ✅ / ❌

Rutas protegidas (requieren contraseña de admin):
  NAV_ADMIN, NAV_CONFIG

Rutas libres (cualquier empleado puede acceder):
  NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES
"""

import flet as ft
from typing import Callable

from database.db_manager import init_db, exportar_ingresos_csv, exportar_finanzas_csv, exportar_congelamientos_csv
from components import (
    Sidebar,
    NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES,
    NAV_ADMIN,   NAV_CONFIG,
    show_auth_dialog,
)
from views import (
    MonitorView, ClientesView, RenovacionesView,
    AdminView,   ConfigView,
)


# ── Conjuntos de rutas ────────────────────────────────────────────────────────
FREE_ROUTES      = {NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES}
PROTECTED_ROUTES = {NAV_ADMIN, NAV_CONFIG}

ROUTE_LABELS = {
    NAV_ADMIN:  "acceder a Administración (Planes y Reportes)",
    NAV_CONFIG: "acceder a Configuración",
}

DEFAULT_VIEW = NAV_MONITOR


def main(page: ft.Page) -> None:
    """
    Función principal de Flet — invocada automáticamente al arrancar.

    Args:
        page: Objeto raíz que representa la ventana del sistema operativo.
    """

    # ── 1. Configuración de la ventana ────────────────────────────
    page.title = "Control de Acceso Gym"
    page.window.width      = 1140
    page.window.height     = 740
    page.window.min_width  = 860
    page.window.min_height = 620

    # ── 2. Tema oscuro ────────────────────────────────────────────
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0D0F14"
    page.padding    = 0

    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.CYAN_400,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    # ── 3. FilePicker para exportación CSV (Fase 7) ───────────────
    # El FilePicker DEBE vivir en main.py y agregarse al page.overlay
    # ANTES de que cualquier vista intente usarlo.

    export_picker = ft.FilePicker()
    finance_picker = ft.FilePicker()
    audit_picker = ft.FilePicker()
    page.services.append(export_picker)
    page.services.append(finance_picker)
    page.services.append(audit_picker)

    def _open_export_picker() -> None:
        """
        Lanza la exportación CSV de Accesos: abre el diálogo 'Guardar como…' en un hilo
        asíncrono y, al recibir la ruta, escribe el archivo y muestra SnackBar.
        """
        async def _run_export():
            ruta = await export_picker.save_file(
                dialog_title="Guardar Reporte de Ingresos",
                file_name="Reporte_Ingresos.csv",
                allowed_extensions=["csv"],
            )

            if not ruta:
                return

            if not ruta.lower().endswith(".csv"):
                ruta += ".csv"

            try:
                n = exportar_ingresos_csv(ruta)
                snack = ft.SnackBar(
                    content=ft.Text(f"✅  Exportación completada: {n} registros guardados en:\n{ruta}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.GREEN_900), duration=5000,
                )
            except Exception as ex:
                snack = ft.SnackBar(
                    content=ft.Text(f"❌  Error al exportar: {ex}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900), duration=5000,
                )
            page.overlay.append(snack)
            snack.open = True
            page.update()

        page.run_task(_run_export)

    def _open_finance_export_picker() -> None:
        """
        Lanza la exportación CSV Financiera: abre el diálogo 'Guardar como…' en un hilo
        asíncrono y, al recibir la ruta, escribe el archivo y muestra SnackBar.
        """
        async def _run_finance_export():
            ruta = await finance_picker.save_file(
                dialog_title="Guardar Reporte Financiero",
                file_name="Reporte_Caja_Gym.csv",
                allowed_extensions=["csv"],
            )

            if not ruta:
                return

            if not ruta.lower().endswith(".csv"):
                ruta += ".csv"

            try:
                n = exportar_finanzas_csv(ruta)
                snack = ft.SnackBar(
                    content=ft.Text(f"💰  Reporte financiero generado: {n} cobros en:\n{ruta}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.BLUE_900), duration=5000,
                )
            except Exception as ex:
                snack = ft.SnackBar(
                    content=ft.Text(f"❌  Error al exportar finanzas: {ex}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900), duration=5000,
                )
            page.overlay.append(snack)
            snack.open = True
            page.update()

        page.run_task(_run_finance_export)

    def _open_audit_export_picker() -> None:
        """
        Lanza la exportación CSV de la Auditoría de Congelamientos.
        """
        async def _run_audit_export():
            ruta = await audit_picker.save_file(
                dialog_title="Guardar Auditoría de Congelamientos",
                file_name="Auditoria_Congelamientos.csv",
                allowed_extensions=["csv"],
            )

            if not ruta:
                return

            if not ruta.lower().endswith(".csv"):
                ruta += ".csv"

            try:
                n = exportar_congelamientos_csv(ruta)
                snack = ft.SnackBar(
                    content=ft.Text(f"✅  Auditoría generada: {n} registros en:\n{ruta}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.GREEN_900), duration=5000,
                )
            except Exception as ex:
                snack = ft.SnackBar(
                    content=ft.Text(f"❌  Error al exportar auditoría: {ex}", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.RED_900), duration=5000,
                )
            page.overlay.append(snack)
            snack.open = True
            page.update()

        page.run_task(_run_audit_export)

    # ── 4. Función de autenticación reutilizable ──────────────────
    def require_auth(
        auth_page: ft.Page,
        on_success: Callable[[], None],
        context_label: str = "esta acción",
    ) -> None:
        show_auth_dialog(
            page=auth_page,
            on_success=on_success,
            context_label=context_label,
        )

    # ── 5. Registro central de vistas ─────────────────────────────
    def _build_view(index: int) -> ft.Control:
        """Instancia la vista correspondiente al índice dado."""
        if index == NAV_MONITOR:
            return MonitorView(require_auth=require_auth)
        elif index == NAV_CLIENTES:
            return ClientesView()
        elif index == NAV_RENOVACIONES:
            return RenovacionesView(require_auth=require_auth)
        elif index == NAV_ADMIN:
            # Inyectamos los callbacks de los FilePicker para exportación CSV
            return AdminView(
                on_export_csv=_open_export_picker,
                on_export_finance_csv=_open_finance_export_picker,
                on_export_audit_csv=_open_audit_export_picker
            )
        elif index == NAV_CONFIG:
            return ConfigView()
        else:
            return MonitorView(require_auth=require_auth)

    # ── 6. Contenedor dinámico de contenido ───────────────────────
    content_area = ft.Container(
        content=_build_view(DEFAULT_VIEW),
        expand=True,
        padding=ft.Padding(left=40, top=36, right=40, bottom=36),
        bgcolor=ft.Colors.TRANSPARENT,
    )

    # ── 7. Función de navegación con control de acceso ────────────
    def navigate(index: int) -> None:
        def _switch_view() -> None:
            content_area.content = _build_view(index)
            page.update()

        if index in FREE_ROUTES:
            _switch_view()
        elif index in PROTECTED_ROUTES:
            require_auth(
                page,
                on_success=_switch_view,
                context_label=ROUTE_LABELS.get(index, "esta sección"),
            )

    # ── 8. Ensamblado del layout ──────────────────────────────────
    sidebar = Sidebar(on_navigate=navigate)

    page.add(
        ft.Row(
            controls=[
                sidebar,
                content_area,
            ],
            expand=True,
            spacing=0,
        )
    )


# ── Punto de entrada ──────────────────────────────────────────────
if __name__ == "__main__":
    from database.db_manager import procesar_congelamientos_automaticos
    init_db()
    procesar_congelamientos_automaticos()
    ft.app(target=main)
