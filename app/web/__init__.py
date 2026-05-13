# =============================================================================
# __init__.py - Definición del Blueprint de la aplicación web
#
# Este módulo crea un blueprint para el manejo de la aplicación web utilizando
# las rutas almacenadas en routes.py dentro del mismo directorio.
#
# =============================================================================

from flask import Blueprint

web_bp = Blueprint('web', __name__)

from . import routes