import google.generativeai as genai
import json
from PIL import Image

# Configura tu API KEY (Usando la que tenías en tu view)
GENAI_API_KEY = "AIzaSyCZkHsDpbhRWiQvUJcuEdRLlI8s-192VU0" 
genai.configure(api_key=GENAI_API_KEY)

def analyze_invoice_image(image_file, smart_input=""):
    """
    Analiza la imagen de la factura usando Gemini 1.5 Flash 
    con reglas estrictas de NIIF y extracción de datos reales.
    """
    try:
        img = Image.open(image_file)
        
        # PROMPT MAESTRO (Le decimos que no invente y que lea aunque esté rotada)
        prompt = f"""
        Actúa como un Auditor Contable experto en Guatemala.
        Lee cuidadosamente la imagen adjunta. IMPORTANTE: La imagen puede estar rotada 90 grados, debes leer el texto de lado.
        
        REGLA DE EXTRACCIÓN: No inventes datos. Si no ves un dato, pon null.
        - Total: Busca el "Total:" o monto final a pagar.
        - NIT: Busca el NIT del emisor en la parte superior.
        - Proveedor: Busca el nombre de la empresa emisora. Ejemplo: "GRUPO ENERGETICO NARANJO".

        CATÁLOGO DE CUENTAS (account_type) - Elige solo UNA de esta lista exacta:
        - "Combustibles y Lubricantes"
        - "Mantenimiento y Reparación de Vehículos"
        - "Papelería y Útiles de Oficina"
        - "Atenciones al Personal y Clientes"
        - "Servicios Públicos y Telefonía"
        - "Mobiliario y Equipo de Computo"
        - "Inventario de Mercadería"
        - "Gastos Generales"

        Contexto adicional del contador: {smart_input}

        Devuelve UNICAMENTE el siguiente formato JSON estricto (sin formato markdown):
        {{
            "provider_name": "Nombre de la empresa",
            "provider_nit": "NIT sin guiones",
            "invoice_series": "Serie",
            "invoice_number": "Número o DTE",
            "total": 0.00,
            "is_fuel": true/false,
            "fuel_type": "regular, diesel o superior",
            "description": "Resumen corto de qué se compró",
            "account_type": "CUENTA_EXACTA_DEL_CATALOGO"
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt, img])
        
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text_response)
        
        # Validaciones de seguridad para evitar errores en Django
        if not data.get('total'): data['total'] = 0.00
        if not data.get('provider_name'): data['provider_name'] = "Proveedor no detectado"
        if not data.get('account_type'): data['account_type'] = "Gastos Generales"
        if data.get('is_fuel') is None: data['is_fuel'] = False
        
        return data

    except Exception as e:
        print(f"Error IA en utils.py: {e}")
        # Si la IA falla por completo, devolvemos un molde vacío para que el contador lo llene manual
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