# Ubicación: core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'  # <--- Asegúrate de que esto diga 'core'
    verbose_name = "Módulo Core de Anaira ERP"
    label = "core"  # <--- Etiqueta única para la app core

    def ready(self):
        import core.signals  # Esto activa las señales
        
# FIN core/apps.py