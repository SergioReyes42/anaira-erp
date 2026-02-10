from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company, Expense, Role, UserRoleCompany # ✅ CORRECTO
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
@receiver(post_save, sender=Expense)
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

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import PurchaseDetail, SaleDetail, Inventory, StockMovement, Warehouse

# --- 1. AUTOMATIZACIÓN DE COMPRAS (ENTRADAS) ---
@receiver(post_save, sender=PurchaseDetail)
def update_stock_on_purchase(sender, instance, created, **kwargs):
    """
    Cuando se guarda un detalle de compra (ej: 10 Laptops),
    sumamos al inventario y creamos el registro en el Kardex.
    """
    if created: # Solo si es nuevo registro
        purchase = instance.purchase
        warehouse = purchase.warehouse # La bodega que seleccionó en el formulario
        
        if not warehouse:
            return # Si no hay bodega, no hacemos nada

        # 1. Buscamos o Creamos el Inventario
        inventory, _ = Inventory.objects.get_or_create(
            product=instance.product,
            warehouse=warehouse,
            defaults={'quantity': 0}
        )

        # 2. Sumamos la cantidad
        inventory.quantity += instance.quantity
        inventory.save()

        # 3. Escribimos en el Kardex (Historial)
        StockMovement.objects.create(
            product=instance.product,
            warehouse=warehouse,
            quantity=instance.quantity,
            movement_type='IN_PURCHASE',
            related_purchase=purchase,
            user=purchase.user, # Asumiendo que Purchase tiene campo user
            comments=f"Compra #{purchase.document_reference or purchase.id}"
        )

# --- 2. AUTOMATIZACIÓN DE VENTAS (SALIDAS) ---
@receiver(post_save, sender=SaleDetail)
def update_stock_on_sale(sender, instance, created, **kwargs):
    """
    Cuando se vende algo, restamos del inventario de la sucursal del vendedor.
    """
    if created:
        sale = instance.sale
        
        # LOGICA INTELIGENTE: ¿De qué bodega sacamos el producto?
        # Intentamos obtener la bodega asociada a la sucursal del empleado/usuario
        warehouse = None
        
        # Opcion A: Si la Venta tiene un campo 'warehouse' explicito
        if hasattr(sale, 'warehouse') and sale.warehouse:
            warehouse = sale.warehouse
        
        # Opcion B: Buscamos la bodega activa de la sucursal del cliente/usuario
        # (Aquí asumimos por simplicidad que tomamos la primera bodega de la sucursal del usuario)
        elif hasattr(sale.user, 'employee') and sale.user.employee.branch:
            branch = sale.user.employee.branch
            warehouse = Warehouse.objects.filter(branch=branch, active=True).first()

        if not warehouse:
            # Si no encontramos bodega, no podemos restar (o usamos una bodega por defecto)
            return 

        # 1. Actualizamos Inventario
        inventory, _ = Inventory.objects.get_or_create(
            product=instance.product,
            warehouse=warehouse,
            defaults={'quantity': 0}
        )
        
        inventory.quantity -= instance.quantity
        inventory.save()

        # 2. Kardex
        StockMovement.objects.create(
            product=instance.product,
            warehouse=warehouse,
            quantity=instance.quantity,
            movement_type='OUT_SALE',
            related_sale=sale,
            user=sale.user,
            comments=f"Venta al cliente {sale.client}"
        )