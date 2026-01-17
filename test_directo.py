import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

def probar_modelo_abierto():
    # Usamos la v1beta pero con el modelo 1.5 que SI tiene cuota gratuita
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "Hola, responde solo: FUNCIONA"}]
        }]
    }

    print(f"📡 Probando con Gemini 1.5 Flash y cuota gratuita...")
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        resultado = response.json()

        if response.status_code == 200:
            texto = resultado['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ ¡AL FIN! Respuesta: {texto}")
        else:
            print(f"❌ ERROR (Código {response.status_code})")
            # Si sale 429 otra vez, es que hay que esperar el tiempo que dice el mensaje
            print(f"Detalle: {json.dumps(resultado, indent=2)}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    probar_modelo_abierto()