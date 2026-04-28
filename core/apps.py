from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core' 
    verbose_name = "Módulo Core de Anaira ERP"
    label = "core" 

    def ready(self):
        import core.signals
