"""
__init__.py — paquete views
Expone todas las funciones constructoras de vista para importarlas desde main.py:
  from views import MonitorView, ClientesView, ...
"""
from .monitor_view      import MonitorView
from .clientes_view     import ClientesView
from .renovaciones_view import RenovacionesView
from .admin_view        import AdminView
from .config_view       import ConfigView

# Vistas heredadas (se mantienen por compatibilidad)
from .home_view     import HomeView
from .users_view    import UsersView
from .settings_view import SettingsView

# Aliases de compatibilidad → apuntan a AdminView
PlanesView   = AdminView
ReportesView = AdminView

__all__ = [
    "MonitorView", "ClientesView", "RenovacionesView",
    "AdminView",   "ConfigView",
    "HomeView",    "UsersView",    "SettingsView",
    "PlanesView",  "ReportesView",
]
