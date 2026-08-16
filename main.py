"""
main.py
-------
Punto de entrada de la aplicación 'Control de Acceso Gym'.

Responsabilidades:
  1. Configurar la ventana principal (tamaño, tema, título).
  2. Instanciar el sidebar y el contenedor de contenido dinámico.
  3. Orquestar el cambio de vista mediante VIEW_MAP.
  4. Gestionar la seguridad: rutas libres vs. rutas protegidas por contraseña.

Flujo de datos:
  Sidebar ──on_navigate(índice)──► navigate(índice)
                                      ├─ ruta libre    → cambia vista directo
                                      └─ ruta protegida → show_auth_dialog()
                                                               └─ on_success → cambia vista

Rutas protegidas (requieren contraseña de admin):
  NAV_PLANES, NAV_REPORTES, NAV_CONFIG

Rutas libres (cualquier empleado puede acceder):
  NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES
"""

import flet as ft
from typing import Callable

from database.db_manager import init_db
from components import (
    Sidebar,
    NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES,
    NAV_PLANES,  NAV_REPORTES, NAV_CONFIG,
    show_auth_dialog,
)
from views import (
    MonitorView, ClientesView, RenovacionesView,
    PlanesView,  ReportesView, ConfigView,
)


# ── Conjuntos de rutas ────────────────────────────────────────────────────────
# Para modificar permisos, basta con mover un índice entre estos conjuntos.
FREE_ROUTES      = {NAV_MONITOR, NAV_CLIENTES, NAV_RENOVACIONES}
PROTECTED_ROUTES = {NAV_PLANES, NAV_REPORTES, NAV_CONFIG}

# Etiquetas descriptivas que aparecen en el diálogo de contraseña
ROUTE_LABELS = {
    NAV_PLANES:       "acceder a Planes",
    NAV_REPORTES:     "acceder a Reportes y Estadísticas",
    NAV_CONFIG:       "acceder a Configuración",
}

DEFAULT_VIEW = NAV_MONITOR


def main(page: ft.Page) -> None:
    """
    Función principal de Flet — invocada automáticamente al arrancar.

    Configura la ventana, aplica el tema oscuro y monta el layout
    [Sidebar | Contenido dinámico] con seguridad de rutas.

    Args:
        page: Objeto raíz que representa la ventana del sistema operativo.
    """

    # ── 1. Configuración de la ventana ────────────────────────────
    page.title = "Control de Acceso Gym"
    page.window.width    = 1140
    page.window.height   = 740
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

    # ── 3. Función de autenticación reutilizable ──────────────────
    def require_auth(
        auth_page: ft.Page,
        on_success: Callable[[], None],
        context_label: str = "esta acción",
    ) -> None:
        """
        Wrapper que invoca show_auth_dialog.

        Centralizar aquí permite cambiar el mecanismo de autenticación
        en el futuro (ej. biométrico, JWT) sin tocar las vistas.

        Args:
            auth_page: La página de Flet donde se mostrará el diálogo.
            on_success: Acción a ejecutar si la contraseña es correcta.
            context_label: Texto descriptivo de la acción protegida.
        """
        show_auth_dialog(
            page=auth_page,
            on_success=on_success,
            context_label=context_label,
        )

    # ── 4. Registro central de vistas ─────────────────────────────
    # MonitorView recibe require_auth para proteger su botón interno.
    # El resto de vistas son stateless y no necesitan el callback.
    def _build_view(index: int) -> ft.Control:
        """Instancia la vista correspondiente al índice dado."""
        if index == NAV_MONITOR:
            return MonitorView(require_auth=require_auth)
        elif index == NAV_CLIENTES:
            return ClientesView()
        elif index == NAV_RENOVACIONES:
            return RenovacionesView()
        elif index == NAV_PLANES:
            return PlanesView()
        elif index == NAV_REPORTES:
            return ReportesView()
        elif index == NAV_CONFIG:
            return ConfigView()
        else:
            return MonitorView(require_auth=require_auth)

    # ── 5. Contenedor dinámico de contenido ───────────────────────
    # Este es el ÚNICO nodo que se reemplaza al navegar.
    content_area = ft.Container(
        content=_build_view(DEFAULT_VIEW),
        expand=True,
        padding=ft.Padding(left=40, top=36, right=40, bottom=36),
        bgcolor=ft.Colors.TRANSPARENT,
    )

    # ── 6. Función de navegación con control de acceso ────────────
    def navigate(index: int) -> None:
        """
        Maneja el cambio de vista con verificación de permisos.

        - Ruta libre      → cambia la vista inmediatamente.
        - Ruta protegida  → muestra el diálogo de contraseña.
                            Solo si es correcta se cambia la vista.
                            Si falla, el usuario se queda en la vista actual.

        Args:
            index: Índice NAV_* de la sección seleccionada en el sidebar.
        """
        def _switch_view() -> None:
            """Realiza el cambio real de contenido."""
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

    # ── 7. Ensamblado del layout ──────────────────────────────────
    sidebar = Sidebar(on_navigate=navigate)

    page.add(
        ft.Row(
            controls=[
                sidebar,       # columna izquierda fija
                content_area,  # columna derecha expandible
            ],
            expand=True,
            spacing=0,
        )
    )


# ── Punto de entrada ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()   # crea gym_data.db y las tablas si no existen
    ft.run(main)
