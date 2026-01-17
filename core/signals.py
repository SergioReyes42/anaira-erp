from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company, Gasto, Role, UserRoleCompany
from .utils import create_tenant_db
from accounting.models import JournalEntry, JournalItem, Account

# =======================================================
# 1. SEÑAL PARA CREAR LA EMPRESA (NO TOCAR)
# =======================================================
@receiver(post_save, sender=Company)
def trigger_db_creation(sender, instance, created, **kwargs):
    if created:
        try:
            create_tenant_db(instance.id)
        except Exception as e:
            print(f"❌ Error creando DB Tenant: {e}")
        
        try:
            role, _ = Role.objects.get_or_create(name="Administrador")
            first_user = instance.assigned_users.first()
            if first_user:
                UserRoleCompany.objects.create(user=first_user, company=instance, role=role)
        except Exception as e:
            print(f"⚠️ Advertencia asignando rol: {e}")

# =======================================================
# 2. SEÑAL CONTABLE (AQUÍ ESTÁ LA CORRECCIÓN)
# =======================================================
@receiver(post_save, sender=Gasto)
def create_accounting_entry_for_expense(sender, instance, created, **kwargs):
    if created:
        try:
            if not Account.objects.filter(company=instance.company).exists():
                return

            # --- CORRECCIÓN AQUÍ: USAR EL CONCEPTO MANUAL ---
            if instance.concepto:
                # Si escribiste algo manual, úsalo y agrega el proveedor entre paréntesis
                descripcion_final = f"{instance.concepto} (Prov: {instance.nombre_emisor})"
            else:
                # Si lo dejaste vacío, usa el formato automático
                descripcion_final = f"Gasto a {instance.nombre_emisor} - Factura {instance.no_factura}"

            # 1. Crear Cabecera
            entry = JournalEntry.objects.create(
                company=instance.company,
                date=instance.fecha,
                description=descripcion_final, # <--- Aquí entra tu texto
                reference=instance.no_factura
            )

            # 2. Buscar Cuentas
            cuenta_gasto = Account.objects.filter(company=instance.company, account_type='EXPENSE').first()
            cuenta_iva = Account.objects.filter(company=instance.company, name__icontains="IVA").first()
            cuenta_caja = Account.objects.filter(company=instance.company, account_type='ASSET').first()

            if not cuenta_gasto or not cuenta_caja:
                return

            monto_sin_iva = float(instance.monto_total) - float(instance.impuesto_iva)

            # 3. Debe (Gasto)
            JournalItem.objects.create(entry=entry, account=cuenta_gasto, debit=monto_sin_iva, credit=0)

            # 4. Debe (IVA)
            if cuenta_iva and instance.impuesto_iva > 0:
                JournalItem.objects.create(entry=entry, account=cuenta_iva, debit=instance.impuesto_iva, credit=0)

            # 5. Haber (Caja/Bancos)
            JournalItem.objects.create(entry=entry, account=cuenta_caja, debit=0, credit=instance.monto_total)
            
        except Exception as e:
            print(f"❌ Error contabilidad: {e}")