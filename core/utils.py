import os
import json
import datetime
import google.genai as genai
from django.conf import settings
from django.core.management import call_command
from dotenv import load_dotenv

# --- CORRECCIÓN IMPORTANTE ---
# Usamos google.generativeai en lugar de google.genai para estandarizar
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Configuración segura
if genai:
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configurando IA: {e}")

# Cargar variables de entorno (API Keys)
load_dotenv()

# =======================================================
# 1. LISTADO DE CUENTAS POR DEFECTO (CATÁLOGO BASE)
# =======================================================
default_accounts = [
    # --- ACTIVOS ---
    {"code": "1-1-01", "name": "Caja General", "type": "ASSET"},
    {"code": "1-1-02", "name": "Bancos Industrial", "type": "ASSET"},
    {"code": "1-1-03", "name": "Bancos Banrural", "type": "ASSET"},
    {"code": "1-1-05", "name": "Cuentas por Cobrar Empleados", "type": "ASSET"}, 
    {"code": "1-1-05-01", "name": "Préstamos a Empleados", "type": "ASSET"}, # <--- NUEVA

    # --- PASIVOS ---
    {"code": "2-1-01", "name": "Proveedores Locales", "type": "LIABILITY"},
    {"code": "2-1-03", "name": "Impuestos por Pagar", "type": "LIABILITY"},
    {"code": "2-1-03-01", "name": "ISR Asalariados por Pagar", "type": "LIABILITY"}, # <--- NUEVA
    {"code": "2-1-03-02", "name": "IGSS por Pagar", "type": "LIABILITY"},             # <--- NUEVA

    # --- CAPITAL ---
    {"code": "3-1-01", "name": "Capital Social", "type": "EQUITY"},
    {"code": "3-1-02", "name": "Utilidad del Ejercicio", "type": "EQUITY"},

    # --- INGRESOS ---
    {"code": "4-1-01", "name": "Venta de Servicios (Fletes)", "type": "INCOME"},
    {"code": "4-1-02", "name": "Otros Ingresos", "type": "INCOME"},

    # --- GASTOS ---
    {"code": "5-1-01", "name": "Sueldos y Salarios", "type": "EXPENSE"},
    {"code": "5-1-02", "name": "Bonificación Incentivo Dto. 37-2001", "type": "EXPENSE"}, # <--- NUEVA
    {"code": "5-1-03", "name": "Combustibles y Lubricantes", "type": "EXPENSE"},
    {"code": "5-1-04", "name": "Repuestos y Mantenimiento", "type": "EXPENSE"},
    {"code": "5-1-05", "name": "Viáticos y Dietas", "type": "EXPENSE"},
    {"code": "5-1-06", "name": "Gastos Administrativos", "type": "EXPENSE"},
    {"code": "5-1-10", "name": "IVA Crédito Fiscal (Gasto Deducible)", "type": "EXPENSE"},
]

# =======================================================
# 2. CREACIÓN DE BASE DE DATOS TENANT (EMPRESA)
# =======================================================
def create_tenant_db(company_id):
    """
    Crea un archivo SQLite independiente para la nueva empresa
    y ejecuta las migraciones iniciales.
    """
    # Definimos la ruta de la base de datos
    db_name = f"company_{company_id}.sqlite3"
    db_path = os.path.join(settings.BASE_DIR, 'tenants', db_name)
    
    # Aseguramos que la carpeta 'tenants' exista
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Configuramos dinámicamente la conexión
    settings.DATABASES[f'company_{company_id}'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'name': db_path,
    }
    
    try:
        # Ejecutamos las migraciones en la nueva base de datos
        call_command('migrate', database=f'company_{company_id}', interactive=False)
        print(f"✅ Base de datos creada exitosamente para Empresa ID: {company_id}")
        
        # Cargar Plan de Cuentas por Defecto
        from accounting.models import Account
        from .models import Company
        
        company = Company.objects.get(id=company_id)
        
        for acc in default_accounts:
            if not Account.objects.filter(company=company, code=acc['code']).exists():
                Account.objects.create(
                    company=company,
                    code=acc['code'],
                    name=acc['name'],
                    account_type=acc['type']
                )
        print("✅ Plan de cuentas base cargado.")
        
    except Exception as e:
        print(f"❌ Error al crear base de datos tenant: {e}")

# =======================================================
# 3. INTELIGENCIA ARTIFICIAL (GEMINI)
# =======================================================
def analyze_invoice_with_ai(image_file):
    """
    Usa Google Gemini para leer la factura (OCR + Inteligencia).
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("⚠️ No se encontró GEMINI_API_KEY en el archivo .env")
        return {}

    genai.configure(api_key=api_key)
    
    # Usamos el modelo rápido
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Analiza esta factura de Guatemala. Extrae los siguientes datos en JSON puro:
    {
        "nit_emisor": "números",
        "nombre_emisor": "nombre comercial",
        "no_factura": "correlativo",
        "serie": "serie",
        "fecha": "YYYY-MM-DD",
        "monto_total": 0.00,
        "monto_idp": 0.00,
        "galones": 0.00,
        "es_combustible": true/false
    }
    Si es combustible, calcula galones aproximados (monto/32). Si no encuentras IDP, pon 0.
    """

    try:
        img_data = image_file.read()
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': img_data}
        ])
        
        # Limpiamos el JSON
        cleaned_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(cleaned_json)
        
        return clean_ai_data(data)

    except Exception as e:
        print(f"❌ Error procesando factura con IA: {e}")
        return {}

def clean_ai_data(datos):
    """Limpia formatos de fecha y números que devuelve la IA"""
    # 1. Limpiar Fecha
    fecha_raw = datos.get('fecha', '')
    if fecha_raw:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                fecha_obj = datetime.datetime.strptime(fecha_raw, fmt)
                datos['fecha'] = fecha_obj.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue