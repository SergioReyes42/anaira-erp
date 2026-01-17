from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SaleInvoice
from inventory.models import StockMovement
from accounting.models import JournalEntry, JournalLine
from core.models import TaxConfiguration
from decimal import Decimal

@receiver(post_save, sender=SaleInvoice)
def process_sale_accounting_and_stock(sender, instance, created, **kwargs):
    if created:
        # 1. Obtener configuración de IVA
        tax_config = TaxConfiguration.objects.filter(company=instance.company).first()
        tax_rate = tax_config.rate / 100 if tax_config else Decimal('0.12')
        
        # 2. Calcular montos
        subtotal = instance.total_amount / (1 + tax_rate)
        iva_monto = instance.total_amount - subtotal

        # 3. Crear Partida Contable
        entry = JournalEntry.objects.create(
            company=instance.company,
            date=instance.date.date(),
            description=f"Venta Factura No. {instance.invoice_number}",
        )

        # DEBE: Caja/Bancos o Clientes (Monto Total)
        JournalLine.objects.create(
            entry=entry,
            account=instance.company.default_payment_account, # Asegúrate de tener este campo o una cuenta fija
            debit=instance.total_amount,
            credit=0
        )

        # HABER: Ventas (Subtotal)
        JournalLine.objects.create(
            entry=entry,
            account=tax_config.sales_tax_account.parent, # O la cuenta de ingresos que definas
            debit=0,
            credit=subtotal
        )

        # HABER: IVA por Pagar (Monto IVA)
        if tax_config:
            JournalLine.objects.create(
                entry=entry,
                account=tax_config.sales_tax_account,
                debit=0,
                credit=iva_monto
            )