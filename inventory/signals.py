from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement
from accounting.models import JournalEntry, JournalLine

@receiver(post_save, sender=StockMovement)
def create_inventory_journal_entry(sender, instance, created, **kwargs):
    if created and instance.movement_type == 'IN':
        # Crear partida de Compra
        entry = JournalEntry.objects.create(
            company=instance.product.company,
            date=instance.date.date(),
            description=f"Compra de Producto: {instance.product.name} (Ref: {instance.reference})",
        )

        # DEBE: Cuenta de Inventario (Activo)
        JournalLine.objects.create(
            entry=entry,
            account=instance.product.inventory_account,
            debit=instance.product.cost_price * instance.quantity,
            credit=0
        )

        # HABER: Cuenta de Pago (Ej: Caja/Bancos o Cuentas por Pagar)
        # Aquí puedes buscar una cuenta por defecto de la empresa
        JournalLine.objects.create(
            entry=entry,
            account=instance.product.company.default_payment_account, # Asumiendo que agregas este campo en Company
            debit=0,
            credit=instance.product.cost_price * instance.quantity
        )
    elif created and instance.movement_type == 'OUT':
        # Crear partida de Venta
        entry = JournalEntry.objects.create(
            company=instance.product.company,
            date=instance.date.date(),
            description=f"Venta de Producto: {instance.product.name} (Ref: {instance.reference})",
        )

        # DEBE: Cuenta de Pago (Ej: Caja/Bancos o Cuentas por Cobrar)
        JournalLine.objects.create(
            entry=entry,
            account=instance.product.company.default_receivable_account, # Asumiendo que agregas este campo en Company
            debit=instance.product.sale_price * instance.quantity,
            credit=0
        )

        # HABER: Cuenta de Inventario (Activo)
        JournalLine.objects.create(
            entry=entry,
            account=instance.product.inventory_account,
            debit=0,
            credit=instance.product.cost_price * instance.quantity
        )
        # HABER: Cuenta de Costo de Ventas (Gasto)
        JournalLine.objects.create(
            entry=entry,
            account=instance.product.cost_account,
            debit=instance.product.cost_price * instance.quantity,
            credit=0
        )
# Nota: Asegúrate de que las cuentas utilizadas (inventory_account, cost_account,
# default_payment_account, default_receivable_account) existan en el catálogo de cuentas    
# de la empresa correspondiente. Además, ajusta la lógica según las necesidades específicas
# de tu plan de cuentas y reglas contables.
# FIN inventory/signals.py
