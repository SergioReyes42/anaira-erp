
# core/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = "Crea roles (Grupos) y asigna permisos del sistema (Django) de forma segura."

    def handle(self, *args, **options):
        # Verifica que existan permisos (requiere haber ejecutado 'migrate')
        if not Permission.objects.exists():
            self.stdout.write(self.style.ERROR(
                "No hay permisos en la base de datos. Ejecuta primero 'python manage.py migrate'."
            ))
            return

        # Define los grupos base
        groups_spec = {
            "Administrador": {"all_perms": True},
            "Supervisor": {"apps": "*", "actions": ["view", "change"]},
            "Operador": {"apps": "*", "actions": ["view"]},
            "Contador": {"apps": ["accounting"], "actions": ["view", "add", "change", "delete"]},
        }

        # Crea/obtiene los grupos
        for gname in groups_spec.keys():
            Group.objects.get_or_create(name=gname)

        # Helper para obtener permisos por app y acciones (view/add/change/delete)
        def get_perms(apps_labels, actions):
            qs = Permission.objects.all()
            if apps_labels != "*":
                qs = qs.filter(content_type__app_label__in=apps_labels)
            # Filtra por prefijo de codename (e.g., view_model, add_model, etc.)
            # Si no quieres regex, puedes hacer union por cada acción con startswith.
            from django.db.models import Q
            cond = Q()
            for act in actions:
                cond |= Q(codename__startswith=f"{act}_")
            return qs.filter(cond)

        # Asigna permisos a cada grupo
        for gname, spec in groups_spec.items():
            group = Group.objects.get(name=gname)
            if spec.get("all_perms"):
                perms = Permission.objects.all()
            else:
                perms = get_perms(spec["apps"], spec["actions"])
            group.permissions.set(perms)
            group.save()

        self.stdout.write(self.style.SUCCESS("Seed de roles y permisos completado con éxito."))
# FIN core/management/commands/seed_roles.py
