from django.core.management.base import BaseCommand
from accounting.models import Account


class Command(BaseCommand):
    help = "Carga/actualiza un plan de cuentas base NIIF/NIC sin duplicados."

    def handle(self, *args, **options):
        cuentas = [
            # 1 ACTIVO
            ("1", "ACTIVO", "ASSET", False),
            ("1.1", "ACTIVO CORRIENTE", "ASSET", False),
            ("1.1.1", "EFECTIVO Y EQUIVALENTES DE EFECTIVO", "ASSET", False),
            ("1.1.1.01", "Caja General", "ASSET", True),
            ("1.1.1.02", "Caja Chica", "ASSET", True),
            ("1.1.1.03", "Bancos Moneda Nacional", "ASSET", True),
            ("1.1.1.04", "Bancos Moneda Extranjera", "ASSET", True),
            ("1.1.1.05", "Depósitos a la Vista", "ASSET", True),
            ("1.1.1.06", "Inversiones de Alta Liquidez", "ASSET", True),
            ("1.1.2", "CUENTAS Y DOCUMENTOS POR COBRAR", "ASSET", False),
            ("1.1.2.01", "Clientes Nacionales", "ASSET", True),
            ("1.1.2.02", "Clientes del Exterior", "ASSET", True),
            ("1.1.2.03", "Documentos por Cobrar", "ASSET", True),
            ("1.1.2.04", "Anticipos a Proveedores", "ASSET", True),
            ("1.1.2.05", "Préstamos a Empleados", "ASSET", True),
            ("1.1.2.06", "Intereses por Cobrar", "ASSET", True),
            ("1.1.2.07", "Estimación Cuentas Incobrables", "ASSET", True),
            ("1.1.3", "INVENTARIOS", "ASSET", False),
            ("1.1.3.01", "Inventario de Mercaderías", "ASSET", True),
            ("1.1.3.02", "Inventario de Materia Prima", "ASSET", True),
            ("1.1.3.03", "Inventario de Productos en Proceso", "ASSET", True),
            ("1.1.3.04", "Inventario de Productos Terminados", "ASSET", True),
            ("1.1.3.05", "Inventario en Tránsito", "ASSET", True),
            ("1.1.3.06", "Provisión por Deterioro de Inventarios", "ASSET", True),
            ("1.1.4", "IMPUESTOS Y CRÉDITOS FISCALES", "ASSET", False),
            ("1.1.4.01", "IVA Crédito Fiscal", "ASSET", True),
            ("1.1.4.02", "ISR Pagos Trimestrales", "ASSET", True),
            ("1.1.4.03", "Retenciones por Recuperar", "ASSET", True),
            ("1.1.4.04", "Crédito Fiscal Importaciones", "ASSET", True),
            ("1.1.5", "GASTOS PAGADOS POR ANTICIPADO", "ASSET", False),
            ("1.1.5.01", "Seguros Pagados Anticipadamente", "ASSET", True),
            ("1.1.5.02", "Alquileres Pagados Anticipadamente", "ASSET", True),
            ("1.1.5.03", "Mantenimientos Pagados Anticipadamente", "ASSET", True),
            ("1.2", "ACTIVO NO CORRIENTE", "ASSET", False),
            ("1.2.1", "PROPIEDAD, PLANTA Y EQUIPO", "ASSET", False),
            ("1.2.1.01", "Terrenos", "ASSET", True),
            ("1.2.1.02", "Edificios", "ASSET", True),
            ("1.2.1.03", "Mobiliario y Equipo", "ASSET", True),
            ("1.2.1.04", "Equipo de Cómputo", "ASSET", True),
            ("1.2.1.05", "Vehículos", "ASSET", True),
            ("1.2.1.06", "Maquinaria", "ASSET", True),
            ("1.2.1.07", "Mejoras a Propiedad Arrendada", "ASSET", True),
            ("1.2.1.08", "Depreciación Acumulada Edificios", "ASSET", True),
            ("1.2.1.09", "Depreciación Acumulada Mobiliario", "ASSET", True),
            ("1.2.1.10", "Depreciación Acumulada Equipo Cómputo", "ASSET", True),
            ("1.2.1.11", "Depreciación Acumulada Vehículos", "ASSET", True),
            ("1.2.1.12", "Depreciación Acumulada Maquinaria", "ASSET", True),
            ("1.2.2", "ACTIVOS INTANGIBLES", "ASSET", False),
            ("1.2.2.01", "Software", "ASSET", True),
            ("1.2.2.02", "Licencias", "ASSET", True),
            ("1.2.2.03", "Marcas y Patentes", "ASSET", True),
            ("1.2.2.04", "Amortización Acumulada Intangibles", "ASSET", True),
            ("1.2.3", "OTROS ACTIVOS NO CORRIENTES", "ASSET", False),
            ("1.2.3.01", "Depósitos en Garantía", "ASSET", True),
            ("1.2.3.02", "Inversiones a Largo Plazo", "ASSET", True),
            ("1.2.3.03", "Cuentas por Cobrar Largo Plazo", "ASSET", True),

            # 2 PASIVO
            ("2", "PASIVO", "LIABILITY", False),
            ("2.1", "PASIVO CORRIENTE", "LIABILITY", False),
            ("2.1.1", "CUENTAS POR PAGAR COMERCIALES", "LIABILITY", False),
            ("2.1.1.01", "Proveedores Nacionales", "LIABILITY", True),
            ("2.1.1.02", "Proveedores del Exterior", "LIABILITY", True),
            ("2.1.1.03", "Documentos por Pagar", "LIABILITY", True),
            ("2.1.1.04", "Anticipos de Clientes", "LIABILITY", True),
            ("2.1.2", "OBLIGACIONES LABORALES", "LIABILITY", False),
            ("2.1.2.01", "Sueldos por Pagar", "LIABILITY", True),
            ("2.1.2.02", "Bonificaciones por Pagar", "LIABILITY", True),
            ("2.1.2.03", "Prestaciones Laborales por Pagar", "LIABILITY", True),
            ("2.1.2.04", "Cuotas Patronales por Pagar", "LIABILITY", True),
            ("2.1.3", "OBLIGACIONES FISCALES", "LIABILITY", False),
            ("2.1.3.01", "IVA Débito Fiscal", "LIABILITY", True),
            ("2.1.3.02", "ISR por Pagar", "LIABILITY", True),
            ("2.1.3.03", "Retenciones ISR por Pagar", "LIABILITY", True),
            ("2.1.3.04", "Retenciones IVA por Pagar", "LIABILITY", True),
            ("2.1.4", "PRÉSTAMOS Y OBLIGACIONES CORTO PLAZO", "LIABILITY", False),
            ("2.1.4.01", "Préstamos Bancarios CP", "LIABILITY", True),
            ("2.1.4.02", "Sobregiros Bancarios", "LIABILITY", True),
            ("2.1.4.03", "Tarjetas de Crédito por Pagar", "LIABILITY", True),
            ("2.2", "PASIVO NO CORRIENTE", "LIABILITY", False),
            ("2.2.1", "PRÉSTAMOS Y OBLIGACIONES LARGO PLAZO", "LIABILITY", False),
            ("2.2.1.01", "Préstamos Bancarios LP", "LIABILITY", True),
            ("2.2.1.02", "Obligaciones Financieras LP", "LIABILITY", True),
            ("2.2.1.03", "Arrendamientos Financieros LP", "LIABILITY", True),
            ("2.2.2", "PROVISIONES LARGO PLAZO", "LIABILITY", False),
            ("2.2.2.01", "Provisión Indemnizaciones", "LIABILITY", True),
            ("2.2.2.02", "Provisión Demandas", "LIABILITY", True),

            # 3 PATRIMONIO
            ("3", "PATRIMONIO", "EQUITY", False),
            ("3.1", "CAPITAL Y APORTES", "EQUITY", False),
            ("3.1.1.01", "Capital Social", "EQUITY", True),
            ("3.1.1.02", "Aportes para Futuras Capitalizaciones", "EQUITY", True),
            ("3.2", "RESERVAS", "EQUITY", False),
            ("3.2.1.01", "Reserva Legal", "EQUITY", True),
            ("3.2.1.02", "Reservas Voluntarias", "EQUITY", True),
            ("3.3", "RESULTADOS ACUMULADOS", "EQUITY", False),
            ("3.3.1.01", "Utilidades de Ejercicios Anteriores", "EQUITY", True),
            ("3.3.1.02", "Pérdidas Acumuladas", "EQUITY", True),
            ("3.3.1.03", "Resultado del Ejercicio", "EQUITY", True),

            # 4 INGRESOS
            ("4", "INGRESOS", "REVENUE", False),
            ("4.1", "INGRESOS OPERATIVOS", "REVENUE", False),
            ("4.1.1.01", "Ventas Locales Gravadas", "REVENUE", True),
            ("4.1.1.02", "Ventas Locales Exentas", "REVENUE", True),
            ("4.1.1.03", "Ventas Exportación", "REVENUE", True),
            ("4.1.1.04", "Ventas de Servicios", "REVENUE", True),
            ("4.1.1.05", "Descuentos y Rebajas sobre Ventas", "REVENUE", True),
            ("4.2", "OTROS INGRESOS", "REVENUE", False),
            ("4.2.1.01", "Ingresos por Intereses", "REVENUE", True),
            ("4.2.1.02", "Ganancia en Venta de Activos", "REVENUE", True),
            ("4.2.1.03", "Diferencial Cambiario Ganado", "REVENUE", True),
            ("4.2.1.04", "Otros Ingresos no Operativos", "REVENUE", True),

            # 5 GASTOS
            ("5", "GASTOS", "EXPENSE", False),
            ("5.1", "GASTOS DE ADMINISTRACIÓN", "EXPENSE", False),
            ("5.1.1.01", "Sueldos Administrativos", "EXPENSE", True),
            ("5.1.1.02", "Bonificaciones Administrativas", "EXPENSE", True),
            ("5.1.1.03", "Prestaciones Laborales Administrativas", "EXPENSE", True),
            ("5.1.1.04", "Honorarios Profesionales", "EXPENSE", True),
            ("5.1.1.05", "Arrendamientos", "EXPENSE", True),
            ("5.1.1.06", "Servicios Básicos", "EXPENSE", True),
            ("5.1.1.07", "Papelería y Útiles", "EXPENSE", True),
            ("5.1.1.08", "Mantenimiento y Reparaciones", "EXPENSE", True),
            ("5.1.1.09", "Seguros", "EXPENSE", True),
            ("5.1.1.10", "Depreciación del Período", "EXPENSE", True),
            ("5.1.1.11", "Amortización del Período", "EXPENSE", True),
            ("5.2", "GASTOS DE VENTAS Y DISTRIBUCIÓN", "EXPENSE", False),
            ("5.2.1.01", "Sueldos de Ventas", "EXPENSE", True),
            ("5.2.1.02", "Comisiones sobre Ventas", "EXPENSE", True),
            ("5.2.1.03", "Publicidad y Promoción", "EXPENSE", True),
            ("5.2.1.04", "Fletes y Acarreos Ventas", "EXPENSE", True),
            ("5.2.1.05", "Viáticos de Ventas", "EXPENSE", True),
            ("5.3", "GASTOS LOGÍSTICOS Y OPERATIVOS", "EXPENSE", False),
            ("5.3.1.01", "Combustibles y Lubricantes", "EXPENSE", True),
            ("5.3.1.02", "Mantenimiento de Flotilla", "EXPENSE", True),
            ("5.3.1.03", "Repuestos y Llantas", "EXPENSE", True),
            ("5.3.1.04", "Peajes y Parqueos", "EXPENSE", True),
            ("5.3.1.05", "Gastos de Bodega", "EXPENSE", True),
            ("5.4", "GASTOS FINANCIEROS", "EXPENSE", False),
            ("5.4.1.01", "Intereses sobre Préstamos", "EXPENSE", True),
            ("5.4.1.02", "Comisiones Bancarias", "EXPENSE", True),
            ("5.4.1.03", "Diferencial Cambiario Perdido", "EXPENSE", True),
            ("5.5", "IMPUESTOS Y TASAS", "EXPENSE", False),
            ("5.5.1.01", "Impuestos Municipales", "EXPENSE", True),
            ("5.5.1.02", "Impuestos no Acreditables", "EXPENSE", True),
            ("5.5.1.03", "Multas y Recargos", "EXPENSE", True),
            ("5.6", "OTROS GASTOS", "EXPENSE", False),
            ("5.6.1.01", "Donaciones", "EXPENSE", True),
            ("5.6.1.02", "Pérdida en Venta de Activos", "EXPENSE", True),
            ("5.6.1.03", "Gastos Extraordinarios", "EXPENSE", True),

            # 6 COSTOS
            ("6", "COSTOS", "EXPENSE", False),
            ("6.1", "COSTO DE VENTAS", "EXPENSE", False),
            ("6.1.1.01", "Costo Mercadería Vendida", "EXPENSE", True),
            ("6.1.1.02", "Fletes sobre Compras", "EXPENSE", True),
            ("6.1.1.03", "Aranceles de Importación", "EXPENSE", True),
            ("6.1.1.04", "Gastos Aduanales", "EXPENSE", True),
            ("6.1.1.05", "Seguros de Importación", "EXPENSE", True),
            ("6.2", "COSTOS DE PRODUCCIÓN", "EXPENSE", False),
            ("6.2.1.01", "Materia Prima Consumida", "EXPENSE", True),
            ("6.2.1.02", "Mano de Obra Directa", "EXPENSE", True),
            ("6.2.1.03", "CIF - Costos Indirectos Fabricación", "EXPENSE", True),
        ]

        creadas = 0
        actualizadas = 0

        for code, name, account_type, is_transactional in cuentas:
            obj, created = Account.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "account_type": account_type,
                    "is_transactional": is_transactional,
                },
            )
            if created:
                creadas += 1
            else:
                cambios = False
                if obj.name != name:
                    obj.name = name
                    cambios = True
                if obj.account_type != account_type:
                    obj.account_type = account_type
                    cambios = True
                if obj.is_transactional != is_transactional:
                    obj.is_transactional = is_transactional
                    cambios = True
                if cambios:
                    obj.save()
                    actualizadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"Plan NIIF/NIC cargado. Creadas: {creadas} | Actualizadas: {actualizadas} | Total definidas: {len(cuentas)}"
        ))
