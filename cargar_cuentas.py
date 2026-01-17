import os
import django

# Configuración del entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anaira_erp.settings')
django.setup()

from core.models import Company, Account, BankAccount

print("--- INICIANDO CARGA DE NOMENCLATURA NIIF ---")

# 1. Obtener Empresa
empresa = Company.objects.first()
if not empresa:
    print("❌ Error: Cree una empresa primero.")
    exit()

print(f"🏢 Empresa: {empresa.name}")

# FUNCION HELPER PARA CREAR CUENTAS EN ORDEN
def crear_cuenta(codigo, nombre, tipo, nivel, padre=None):
    cuenta, created = Account.objects.get_or_create(
        code=codigo,
        company=empresa,
        defaults={
            'name': nombre,
            'account_type': tipo,
            'level': nivel,
            'parent': padre
        }
    )
    estado = "✅ Creada" if created else "ℹ️ Ya existe"
    print(f"{estado}: [{codigo}] {nombre}")
    return cuenta

# ==========================================
# NIVEL 1: CLASES PRINCIPALES
# ==========================================
activo = crear_cuenta("1", "ACTIVO", "Activo", 1)
pasivo = crear_cuenta("2", "PASIVO", "Pasivo", 1)
patrimonio = crear_cuenta("3", "PATRIMONIO", "Capital", 1)
ingresos = crear_cuenta("4", "INGRESOS", "Ingreso", 1)
gastos = crear_cuenta("5", "GASTOS", "Gasto", 1)

# ==========================================
# NIVEL 2: GRUPOS (CORRIENTE / NO CORRIENTE)
# ==========================================
act_corriente = crear_cuenta("1.1", "ACTIVO CORRIENTE", "Activo", 2, activo)
act_no_corriente = crear_cuenta("1.2", "ACTIVO NO CORRIENTE", "Activo", 2, activo)

pas_corriente = crear_cuenta("2.1", "PASIVO CORRIENTE", "Pasivo", 2, pasivo)
gastos_admin = crear_cuenta("5.1", "GASTOS DE ADMINISTRACIÓN", "Gasto", 2, gastos)

# ==========================================
# NIVEL 3: RUBROS NIIF (CUENTAS DE MAYOR)
# ==========================================
# 1.1.01 Efectivo y Equivalentes (Antes llamado Caja y Bancos)
efectivo = crear_cuenta("1.1.01", "EFECTIVO Y EQUIVALENTES", "Activo", 3, act_corriente)

# 1.1.02 Cuentas por Cobrar Comerciales
clientes = crear_cuenta("1.1.02", "CUENTAS POR COBRAR COMERCIALES", "Activo", 3, act_corriente)

# 1.1.03 Anticipos a Empleados (Para su módulo de RRHH)
anticipos = crear_cuenta("1.1.03", "ANTICIPOS A EMPLEADOS", "Activo", 3, act_corriente)

# 2.1.01 Cuentas por Pagar (Proveedores)
proveedores = crear_cuenta("2.1.01", "CUENTAS POR PAGAR COMERCIALES", "Pasivo", 3, pas_corriente)

# 5.1.01 Sueldos y Salarios (Para Nómina)
sueldos = crear_cuenta("5.1.01", "SUELDOS Y BENEFICIOS", "Gasto", 3, gastos_admin)

# ==========================================
# NIVEL 4: CUENTAS TRANSACCIONALES (AQUÍ SE REGISTRA)
# ==========================================

# Bancos Específicos
banco_bi_contable = crear_cuenta("1.1.01.001", "Banco Industrial S.A.", "Activo", 4, efectivo)
banco_bam_contable = crear_cuenta("1.1.01.002", "Banco Agromercantil", "Activo", 4, efectivo)
caja_chica = crear_cuenta("1.1.01.003", "Caja Chica", "Activo", 4, efectivo)

# Cuentas para RRHH
prestamos_emp = crear_cuenta("1.1.03.001", "Préstamos al Personal", "Activo", 4, anticipos)
gasto_sueldo = crear_cuenta("5.1.01.001", "Sueldos Ordinarios", "Gasto", 4, sueldos)
gasto_bono = crear_cuenta("5.1.01.002", "Bonificación Incentivo", "Gasto", 4, sueldos)
cuota_patronal = crear_cuenta("5.1.01.003", "Cuota Patronal IGSS", "Gasto", 4, sueldos)

# ==========================================
# VINCULACIÓN BANCARIA (MÓDULO DE TESORERÍA)
# ==========================================
print("\n--- VINCULANDO TESORERÍA ---")

# Creamos la cuenta bancaria operativa y la enlazamos a la contable 1.1.01.001
BankAccount.objects.get_or_create(
    account_number="BI-001-9999-00",
    company=empresa,
    defaults={
        'bank_name': "Banco Industrial",
        'currency': "GTQ",
        'accounting_account': banco_bi_contable, # <--- ENLACE CLAVE
        'current_balance': 50000.00
    }
)
print("✅ Cuenta de Banco Industrial creada y enlazada a cuenta 1.1.01.001")

print("\n--- PROCESO NIIF TERMINADO CON ÉXITO ---")