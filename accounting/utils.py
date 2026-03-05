import google.generativeai as genai
import json
from PIL import Image

# Configura tu API KEY 
GENAI_API_KEY = "AIzaSyCZkHsDpbhRWiQvUJcuEdRLlI8s-192VU0" 
genai.configure(api_key=GENAI_API_KEY)

def analyze_invoice_image(image_file, smart_input=""):
    """
    Cerebro IA Francotirador: Analiza facturas con reglas SAT Guatemala.
    """
    try:
        img = Image.open(image_file)
        
        # PROMPT MAESTRO (Entrenado para Facturación Electrónica en Línea - FEL)
        prompt = f"""
        Eres un Auditor Fiscal Experto de la SAT en Guatemala.
        Tu misión es extraer los datos exactos de esta factura electrónica (FEL) o recibo.
        
        REGLAS DE ORO (Si rompes una, el sistema falla):
        1. CERO INVENTOS: Si un dato no es visible, legible o no existe, devuelve exactamente null. La imagen puede estar rotada, ajusta tu lectura.
        2. TOTAL: Busca "TOTAL", "Q.", "GTQ". Devuelve SOLO el número final (ej. 150.50).
        3. NIT: Extrae el NIT del emisor. Mantenlo con su guion si lo tiene (ej. 123456-7).
        4. DTE/SERIE: Las FEL guatemaltecas tienen Serie (ej. 8A1B2C3D o A) y Número de autorización. Extrae ambos.
        5. COMBUSTIBLE: Si ves "Galones", "Diesel", "Super", "Regular", o es una gasolinera (Shell, Puma, Texaco, Uno), is_fuel debe ser true obligatoriamente.
        
        CATÁLOGO DE CUENTAS (Debes elegir estrictamente UNA):
        - "Combustibles y Lubricantes"
        - "Mantenimiento y Reparación de Vehículos"
        - "Papelería y Útiles de Oficina"
        - "Atenciones al Personal y Clientes"
        - "Servicios Públicos y Telefonía"
        - "Mobiliario y Equipo de Computo"
        - "Inventario de Mercadería"
        - "Gastos Generales"

        Contexto adicional del contador: {smart_input}

        Devuelve el resultado estrictamente en este esquema JSON:
        {{
            "provider_name": "Nombre completo de la empresa",
            "provider_nit": "NIT del emisor",
            "invoice_series": "Serie de la factura",
            "invoice_number": "Número de factura o DTE",
            "total": 0.00,
            "is_fuel": true o false,
            "fuel_type": "regular, diesel, super o null",
            "description": "Qué se compró (máximo 5 palabras)",
            "account_type": "CUENTA_EXACTA_DEL_CATALOGO"
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 🔥 LA MAGIA ESTÁ AQUÍ: Configuración de Francotirador
        response = model.generate_content(
            [prompt, img],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json", # Obliga a devolver un JSON real de forma nativa
                temperature=0.0, # Temperatura 0 = Cero alucinaciones, precisión absoluta
            )
        )
        
        # Ya no necesitamos hacer replace('```json'), la API garantiza el formato
        data = json.loads(response.text)
        
        # Filtros de seguridad blindados para evitar pantallas amarillas de error en Django
        data['total'] = float(data.get('total') or 0.00)
        data['provider_name'] = data.get('provider_name') or "Proveedor no detectado"
        data['account_type'] = data.get('account_type') or "Gastos Generales"
        data['is_fuel'] = bool(data.get('is_fuel'))
        
        return data

    except Exception as e:
        print(f"🔥 Error Crítico en IA: {e}")
        # Si la foto está totalmente en negro o ilegible, no rompemos el ERP
        return {
            "provider_name": "Error de Lectura IA",
            "provider_nit": "",
            "invoice_series": "",
            "invoice_number": "",
            "total": 0.00,
            "is_fuel": False,
            "fuel_type": "",
            "description": "Hubo un error al leer la imagen",
            "account_type": "Gastos Generales"
        }