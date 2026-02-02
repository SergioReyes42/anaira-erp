# core/ai_brain.py
import google.generativeai as genai
from django.conf import settings
import json
from datetime import date
import logging
import re  # <--- AGREGADO: Importante para la función de texto

# Configurar la IA con su llave
genai.configure(api_key=settings.GEMINI_API_KEY)

# Configuración del modelo (GEMINI 2.0)
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash", 
    generation_config=generation_config,
)

# --- FUNCIÓN 1: PARA IMÁGENES (Gemini) ---
# (Imports siguen igual...)
import google.generativeai as genai
from django.conf import settings
import json
from datetime import date
import logging
import re

genai.configure(api_key=settings.GEMINI_API_KEY)
generation_config = {"temperature": 0.1, "top_p": 1, "top_k": 32, "max_output_tokens": 8192}
model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=generation_config)

def analizar_documento_ia(imagen, contexto=None):
    resultado = {'exito': False, 'tipo_detectado': 'DESCONOCIDO', 'datos': {}}

    try:
        img_bytes = imagen.read()
        
        prompt_base = "Eres un asistente experto en ERP. Analiza la imagen y extrae datos en JSON estricto."

        if contexto == 'GASTO':
            prompt_especifico = """Contexto: FACTURA COMPRA. Extrae: "proveedor", "total", "fecha", "serie", "nit"."""
        
        elif contexto == 'IN':
            prompt_especifico = """Contexto: BOLETA DEPOSITO. Extrae: "monto", "no_boleta", "fecha"."""
            
        elif contexto == 'OUT':
            prompt_especifico = """Contexto: CHEQUE. Extrae: "monto", "numero_cheque", "beneficiario", "fecha"."""
            
        elif contexto == 'COTIZACION':
            prompt_especifico = """Contexto: PEDIDO CLIENTE. Extrae: "cliente", "productos" (array), "observaciones"."""
        
        # --- NUEVO: CONTEXTO PRODUCTO ---
        elif contexto == 'PRODUCTO':
            prompt_especifico = """
            Contexto: ETIQUETA O CAJA DE PRODUCTO.
            Extrae:
            - "nombre": Nombre comercial del producto.
            - "descripcion": Características clave (peso, tamaño, modelo).
            - "marca": Marca del fabricante.
            - "codigo": Si ves un código de barras o SKU escríbelo.
            """
        else:
            prompt_especifico = "Extrae datos generales."

        full_prompt = prompt_base + prompt_especifico

        response = model.generate_content([{'mime_type': imagen.content_type, 'data': img_bytes}, full_prompt])
        
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        datos_json = json.loads(texto_limpio)
        
        resultado['exito'] = True
        resultado['datos'] = datos_json
        
    except Exception as e:
        print(f"Error IA: {e}")
        resultado['mensaje'] = str(e)

    imagen.seek(0)
    return resultado

# --- FUNCIÓN 2: PARA TEXTO (Regex) ---
def analizar_texto_bancario(texto):
    """
    Analiza texto natural para extraer datos bancarios usando Lógica Regex.
    Ej: "Pago de luz Q300" -> {amount: 300, description: "Pago de luz", movement_type: "OUT"}
    """
    texto = texto.lower().strip()
    respuesta = {
        'description': texto.capitalize(),  
        'amount': None,
        'date': date.today().strftime('%Y-%m-%d'), 
        'movement_type': 'OUT' # Ante la duda, asumimos que es Gasto
    }

    # 1. DETECTAR MONTO
    monto_match = re.search(r'q?\.?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', texto)
    if monto_match:
        raw_num = monto_match.group(1).replace(',', '') # Quitar comas
        respuesta['amount'] = raw_num
        
        # Limpiamos la descripción quitando el monto
        desc_clean = re.sub(r'q?\.?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', '', texto).strip()
        respuesta['description'] = desc_clean.capitalize()

    # 2. DETECTAR TIPO
    palabras_ingreso = ['deposito', 'depósito', 'ingreso', 'cobro', 'venta', 'recibí', 'abono', 'cliente']
    if any(palabra in texto for palabra in palabras_ingreso):
        respuesta['movement_type'] = 'IN'
    
    return respuesta