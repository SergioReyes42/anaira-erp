# core/ai_brain.py
import google.generativeai as genai
from django.conf import settings
import json
from datetime import date
import logging

# Configurar la IA con su llave
genai.configure(api_key=settings.GEMINI_API_KEY)

# Configuración del modelo (ACTUALIZADA A GEMINI 2.0)
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    # CAMBIO AQUÍ: Usamos el modelo que sí apareció en su lista
    model_name="gemini-2.0-flash", 
    generation_config=generation_config,
)

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
        # 1. Preparamos la imagen para enviarla a Google
        # Django tiene la imagen en memoria, necesitamos sus bytes
        img_bytes = imagen.read()
        
        # 2. Definimos el Prompt (Las instrucciones para la IA) según el contexto
        prompt_base = """
        Eres un asistente contable experto de la empresa 'Anaira ERP'. 
        Tu trabajo es analizar esta imagen y extraer datos clave en formato JSON estricto.
        NO escribas nada más que el JSON.
        """

        if contexto == 'GASTO':
            prompt_especifico = """
            La imagen es una FACTURA de compra o recibo. Extrae:
            - "proveedor": Nombre del establecimiento.
            - "total": Monto total numérico (solo numero).
            - "fecha": Fecha en formato YYYY-MM-DD (si no hay año, asume 2026).
            - "serie": Número de serie o factura.
            - "nit": NIT del proveedor.
            - "es_combustible": true si es gasolina/diesel, false si no.
            """
        elif contexto == 'IN': # Depósitos
            prompt_especifico = """
            La imagen es una BOLETA DE DEPÓSITO o transferencia entrante. Extrae:
            - "monto": Monto total depositado (solo numero).
            - "no_boleta": Número de boleta o referencia.
            - "banco_receptor": Banco donde se depositó.
            - "fecha": Fecha en formato YYYY-MM-DD.
            """
        elif contexto == 'OUT': # Cheques
            prompt_especifico = """
            La imagen es un CHEQUE o comprobante de pago. Extrae:
            - "monto": Monto numérico.
            - "numero_cheque": Número del cheque.
            - "beneficiario": Nombre de a quién se paga.
            - "fecha": Fecha en formato YYYY-MM-DD.
            """
        else: # Genérico
            prompt_especifico = """
            Identifica qué documento es (Cheque, Factura, Depósito) y extrae:
            - "tipo": Tipo de documento.
            - "monto": Monto total.
            - "referencia": Cualquier número de identificación.
            """

        full_prompt = prompt_base + prompt_especifico

        # 3. Enviamos a Gemini
        # Pasamos el tipo MIME (ej: image/jpeg) y los datos
        response = model.generate_content([
            {'mime_type': imagen.content_type, 'data': img_bytes},
            full_prompt
        ])

        # 4. Procesamos la respuesta
        texto_respuesta = response.text
        
        # Limpieza: A veces Gemini envuelve el JSON en ```json ... ```
        texto_limpio = texto_respuesta.replace("```json", "").replace("```", "").strip()
        
        datos_json = json.loads(texto_limpio)
        
        # 5. Éxito
        resultado['exito'] = True
        resultado['datos'] = datos_json
        
        # Determinar tipo detectado basado en el contexto
        if contexto == 'GASTO': resultado['tipo_detectado'] = 'FACTURA'
        elif contexto == 'IN': resultado['tipo_detectado'] = 'DEPOSITO'
        elif contexto == 'OUT': resultado['tipo_detectado'] = 'CHEQUE'
        
        print("--- ANÁLISIS IA EXITOSO ---")
        print(datos_json)

    except Exception as e:
        print(f"--- ERROR IA: {str(e)} ---")
        resultado['mensaje'] = f"Error al procesar con IA: {str(e)}"

    # Importante: Regresar el puntero del archivo al inicio por si Django necesita guardarlo después
    imagen.seek(0)
    
    return resultado