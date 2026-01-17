
from django.apps import AppConfig

class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting"
    label = "accounting"  # etiqueta única y distinta de 'accounts'
    verbose_name = "Módulo de Contabilidad"