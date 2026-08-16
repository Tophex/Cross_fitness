"""
__init__.py — paquete components
Exporta el Sidebar y todas las constantes NAV_* para importarlas desde main.py:
  from components import Sidebar, NAV_MONITOR, NAV_CLIENTES, ...
"""
from .sidebar import (
    Sidebar,
    NAV_MONITOR,
    NAV_CLIENTES,
    NAV_RENOVACIONES,
    NAV_PLANES,
    NAV_REPORTES,
    NAV_CONFIG,
)
from .auth_dialog import show_auth_dialog

__all__ = [
    "Sidebar",
    "NAV_MONITOR", "NAV_CLIENTES", "NAV_RENOVACIONES",
    "NAV_PLANES",  "NAV_REPORTES", "NAV_CONFIG",
    "show_auth_dialog",
]
