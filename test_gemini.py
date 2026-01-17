import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

def test_cuenta_pro():
    print(f"📡 Probando conexión con cuenta habilitada...")
    try:
        genai.configure(api_key=api_key)
        
        # Ahora que tienes habilitada la API en Cloud, 
        # probamos con el modelo más avanzado que tenías en tu lista
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content("Hola, confirma si ya tengo acceso total para Anaira ERP.")
        
        print("\n--- ✅ ¡CONEXIÓN EXITOSA! ---")
        print(f"Respuesta de Gemini: {response.text}")
        print("----------------------------")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_cuenta_pro()