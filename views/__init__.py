"""
__init__.py — paquete views
Expone todas las funciones constructoras de vista para importarlas desde main.py:
  from views import MonitorView, ClientesView, ...
"""
from .monitor_view      import MonitorView
from .clientes_view     import ClientesView
from .renovaciones_view import RenovacionesView
from .planes_view       import PlanesView
from .reportes_view     import ReportesView
from .config_view       import ConfigView

# Vistas heredadas (se mantienen por compatibilidad)
from .home_view     import HomeView
from .users_view    import UsersView
from .settings_view import SettingsView

__all__ = [
    "MonitorView", "ClientesView", "RenovacionesView",
    "PlanesView",  "ReportesView", "ConfigView",
    "HomeView",    "UsersView",    "SettingsView",
]
