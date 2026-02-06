# core/logic.py
from gettext import translation
from django.db import transaction  # <--- ESTE ES EL QUE LE FALTA
from django.db.models import F
from .models import Inventory, Warehouse, StockMovement

def gestionar_salida_stock(user, product, quantity, reference="Venta"):
    """
    Esta función es el CEREBRO. Decide automáticamente de qué bodega sacar el producto.
    Reglas:
    1. Busca en la Sucursal del Empleado.
    2. Si no hay, busca en la Bodega Principal (Central).
    3. Si no hay, devuelve Error.
    """
    
    # 1. IDENTIFICAR AL USUARIO Y SU SUCURSAL
    empleado = getattr(user, 'employee', None)
    sucursal_usuario = empleado.branch if empleado else None
    
    bodega_seleccionada = None
    inventario_record = None

    # 2. INTENTO A: Buscar en la bodega de SU sucursal
    if sucursal_usuario:
        # Buscamos inventarios en bodegas de ESA sucursal con stock suficiente
        inventario_local = Inventory.objects.filter(
            warehouse__branch=sucursal_usuario,
            product=product,
            quantity__gte=quantity # Que tenga suficiente cantidad
        ).first()
        
        if inventario_local:
            bodega_seleccionada = inventario_local.warehouse
            inventario_record = inventario_local

    # 3. INTENTO B: Si falló la local, buscar en la CENTRAL (Principal)
    if not bodega_seleccionada:
        inventario_central = Inventory.objects.filter(
            warehouse__is_main=True, # Asumiendo que marcó una como 'is_main'
            product=product,
            quantity__gte=quantity
        ).first()
        
        if inventario_central:
            bodega_seleccionada = inventario_central.warehouse
            inventario_record = inventario_central

    # 4. RESULTADO FINAL
    if not bodega_seleccionada or not inventario_record:
        return False, f"Stock insuficiente para {product.name} (Req: {quantity})"

    # 5. EJECUTAR EL DESCUENTO (Mano Dura)
    # A. Restamos del Inventario Específico (La Bodega Real)
    inventario_record.quantity = F('quantity') - quantity
    inventario_record.save()
    
    # B. Restamos del Global (Para referencia rápida en listas)
    product.stock = F('stock') - quantity
    product.save()

    # C. Dejamos huella en el Kardex Detallado
    StockMovement.objects.create(
        product=product,
        warehouse=bodega_seleccionada,
        quantity=quantity * -1, # Negativo porque es salida
        movement_type='OUT_SALE',
        user=user,
        comments=f"{reference} - Despachado desde {bodega_seleccionada.name}"
    )

    return True, f"Despachado de {bodega_seleccionada.name}"

@transaction.atomic
def realizar_traslado_entre_bodegas(user, product, bodega_origen, bodega_destino, cantidad, comentario=""):
    """
    Mueve mercadería de una bodega a otra.
    1. Verifica stock en origen.
    2. Resta de Origen.
    3. Suma en Destino.
    4. Registra doble movimiento en Kardex (Salida y Entrada).
    """
    
    # 1. VERIFICAR ORIGEN
    # Buscamos si existe el registro de inventario en el origen
    inv_origen = Inventory.objects.filter(warehouse=bodega_origen, product=product).first()
    
    if not inv_origen or inv_origen.quantity < cantidad:
        return False, f"Stock insuficiente en {bodega_origen.name}. Disponible: {inv_origen.quantity if inv_origen else 0}"

    # 2. GESTIONAR DESTINO
    # Buscamos si ya existe inventario en destino, si no, lo creamos
    inv_destino, created = Inventory.objects.get_or_create(
        warehouse=bodega_destino, 
        product=product,
        defaults={'quantity': 0}
    )

    # 3. EJECUTAR EL MOVIMIENTO (Matemática pura)
    inv_origen.quantity -= cantidad
    inv_origen.save()

    inv_destino.quantity += cantidad
    inv_destino.save()

    # NOTA: No tocamos Product.stock (global) porque el total de la empresa sigue siendo el mismo,
    # solo cambió de lugar.

    # 4. REGISTRAR EN KARDEX (Doble partida)
    
    # A. La Salida de Origen
    StockMovement.objects.create(
        product=product,
        warehouse=bodega_origen,
        quantity=cantidad * -1, # Negativo visualmente
        movement_type='TRANSFER_OUT',
        related_transfer_id=inv_origen.id, # Usamos un ID temporal o grupo
        user=user,
        comments=f"Traslado hacia {bodega_destino.name}. {comentario}"
    )

    # B. La Entrada en Destino
    StockMovement.objects.create(
        product=product,
        warehouse=bodega_destino,
        quantity=cantidad, # Positivo
        movement_type='TRANSFER_IN',
        related_transfer_id=inv_origen.id,
        user=user,
        comments=f"Recibido desde {bodega_origen.name}. {comentario}"
    )

    return True, f"Traslado exitoso: {cantidad} unidades movidas a {bodega_destino.name}"