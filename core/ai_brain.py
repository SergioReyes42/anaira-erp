import google.generativeai as genai
from django.conf import settings
import json
from datetime import date
import logging
import re # IMPORTANTE: Agregado para el análisis de texto

# Configurar la IA con su llave
genai.configure(api_key=settings.GEMINI_API_KEY)

# Configuración del modelo
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

def analizar_documento_ia(imagen, contexto=None):
    # ... [SU CÓDIGO DE GEMINI PARA IMÁGENES SE QUEDA IGUAL AQUÍ] ...
    # (Para ahorrar espacio, asuma que aquí está todo el bloque que usted ya tiene
    # para analizar_documento_ia. No lo borre, déjelo tal cual).
    
    # ... Fin de analizar_documento_ia ...
    pass # Placeholder visual


# --- NUEVA FUNCIÓN AGREGADA PARA EL FORMULARIO DE BANCOS ---
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
    # Busca patrones como: Q500, Q.500, 500.00, 500
    monto_match = re.search(r'q?\.?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', texto)
    if monto_match:
        raw_num = monto_match.group(1).replace(',', '') # Quitar comas
        respuesta['amount'] = raw_num
        
        # Limpiamos la descripción quitando el monto
        desc_clean = re.sub(r'q?\.?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', '', texto).strip()
        respuesta['description'] = desc_clean.capitalize()

    # 2. DETECTAR TIPO (Semántica Básica)
    palabras_ingreso = ['deposito', 'depósito', 'ingreso', 'cobro', 'venta', 'recibí', 'abono', 'cliente']
    
    # Si encuentra alguna palabra clave, lo marca como IN (Ingreso)
    if any(palabra in texto for palabra in palabras_ingreso):
        respuesta['movement_type'] = 'IN'
    
    return respuesta