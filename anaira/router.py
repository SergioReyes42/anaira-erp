class CompanyRouter:
    """
    Controla qué base de datos usa cada consulta dependiendo del contexto.
    """
    def db_for_read(self, model, **hints):
        # Si estamos consultando usuarios o la lista de empresas, usar la base 'default'
        if model._meta.app_label in ['admin', 'auth', 'contenttypes', 'sessions', 'core']:
            return 'default'
        # Para lo demás (contabilidad, ventas, etc), el middleware decidirá
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in ['admin', 'auth', 'contenttypes', 'sessions', 'core']:
            return 'default'
        return None

class CompanyRouter:
    # Apps que SIEMPRE deben estar en la base Maestra (db_main)
    shared_apps = ['accounts', 'admin', 'auth', 'contenttypes', 'sessions', 'core']

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.shared_apps:
            return 'default'
        from core.middleware import get_current_db
        return get_current_db()

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.shared_apps:
            return 'default'
        from core.middleware import get_current_db
        return get_current_db()

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.shared_apps:
            return db == 'default'
        return None