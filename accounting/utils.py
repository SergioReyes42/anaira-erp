import random
import re

def analyze_invoice_image(image, manual_text=""):
    """
    Simula el motor de IA (Gemini/OCR).
    Analiza el texto o imagen y retorna la estructura de datos lista.
    """
    text_data = manual_text.lower()
    
    # 1. VALORES POR DEFECTO (Si la IA no entiende nada)
    data = {
        'provider_name': 'Consumidor Final',
        'provider_nit': 'CF',
        'invoice_series': 'A',
        'invoice_number': str(random.randint(1000, 99999)),
        'description': manual_text or "Gasto Varios",
        'total': float(random.randint(100, 3000)), # Simulado
        'account_type': 'Gastos Generales', # Cuenta por defecto
        'is_fuel': False,
        'fuel_type': None # 'regular', 'super', 'diesel'
    }

    # 2. REGLAS DE INTELIGENCIA ARTIFICIAL (Categorización)
    
    # --- CASO A: COMBUSTIBLES (Detectar Shell, Puma, Texaco, Gasolina) ---
    if any(x in text_data for x in ['shell', 'puma', 'texaco', 'uno', 'gasolina', 'diesel', 'combustible']):
        data['account_type'] = 'Combustibles y Lubricantes'
        data['is_fuel'] = True
        data['provider_name'] = 'ESTACION DE SERVICIO'
        
        # Intentar detectar tipo de combustible para el IDP
        if 'diesel' in text_data:
            data['fuel_type'] = 'diesel'
            data['description'] = 'Compra de Diesel'
        elif 'regular' in text_data:
            data['fuel_type'] = 'regular'
            data['description'] = 'Compra de Gasolina Regular'
        else:
            data['fuel_type'] = 'super' # Default a Super si no especifica
            data['description'] = 'Compra de Gasolina Super'

    # --- CASO B: TECNOLOGÍA (Detectar Laptop, Mouse, Teclado) ---
    elif any(x in text_data for x in ['laptop', 'computadora', 'mouse', 'teclado', 'monitor', 'intel', 'dell']):
        data['account_type'] = 'Equipo de Cómputo'
        data['provider_name'] = 'INTELAF S.A.' # Ejemplo
        data['description'] = 'Compra de Equipo Tecnológico'

    # --- CASO C: VEHÍCULOS (Llantas, Aceite, Servicios) ---
    elif any(x in text_data for x in ['llanta', 'pinchazo', 'aceite', 'frenos', 'taller']):
        data['account_type'] = 'Repuestos y Mantenimiento Vehículos'
        data['description'] = 'Mantenimiento de Flotilla'
        

    # --- CASO D: RESTAURANTES ---
    elif any(x in text_data for x in ['mcdonalds', 'comida', 'almuerzo', 'restaurante']):
        data['account_type'] = 'Gastos de Representación (Alimentos)'
        data['provider_name'] = 'RESTAURANTES S.A.'


    return data
