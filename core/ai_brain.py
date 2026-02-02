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
def analizar_documento_ia(imagen, contexto=None):
    # --- DEBUG: IMPRIMIR MODELOS DISPONIBLES ---
    print("--- CONSULTANDO MODELOS DISPONIBLES ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listando modelos: {e}")
    # -------------------------------------------
    
    resultado = {
        'exito': False,
        'tipo_detectado': 'DESCONOCIDO',
        'datos': {}
    }

    try:
        # 1. Preparamos la imagen
        img_bytes = imagen.read()
        
        # 2. Definimos el Prompt
        prompt_base = """
        Eres un asistente contable experto de la empresa 'Anaira ERP'. 
        Tu trabajo es analizar esta imagen y extraer datos clave en formato JSON estricto.
        NO escribas nada más que el JSON.
        """

        if contexto == 'GASTO':
            prompt_especifico = """
            La imagen es una FACTURA de compra o recibo. Extrae:
            - "proveedor": Nombre.
            - "total": Monto total numérico.
            - "fecha": YYYY-MM-DD.
            - "serie": Serie o factura.
            """
        elif contexto == 'IN': # Depósitos
            prompt_especifico = """
            La imagen es una BOLETA DE DEPÓSITO. Extrae:
            - "monto": Monto total depositado (solo numero).
            - "no_boleta": Número de boleta o referencia.
            - "fecha": YYYY-MM-DD.
            """
        elif contexto == 'OUT': # Cheques
            prompt_especifico = """
            La imagen es un CHEQUE. Extrae:
            - "monto": Monto numérico.
            - "numero_cheque": Número del cheque.
            - "beneficiario": Nombre.
            - "fecha": YYYY-MM-DD.
            """
        else: # Genérico
            prompt_especifico = """
            Identifica documento y extrae: "monto", "referencia", "fecha", "descripcion".
            """

        full_prompt = prompt_base + prompt_especifico

        # 3. Enviamos a Gemini
        response = model.generate_content([
            {'mime_type': imagen.content_type, 'data': img_bytes},
            full_prompt
        ])

        # 4. Procesamos la respuesta
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        datos_json = json.loads(texto_limpio)
        
        # 5. Éxito
        resultado['exito'] = True
        resultado['datos'] = datos_json
        
        if contexto == 'IN': resultado['tipo_detectado'] = 'DEPOSITO'
        elif contexto == 'OUT': resultado['tipo_detectado'] = 'CHEQUE'
        
        print("--- ANÁLISIS IA EXITOSO ---")
        print(datos_json)

    except Exception as e:
        print(f"--- ERROR IA: {str(e)} ---")
        resultado['mensaje'] = f"Error al procesar con IA: {str(e)}"

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