import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

def listar_modelos():
    try:
        genai.configure(api_key=api_key)
        print("🔍 Consultando modelos disponibles para tu cuenta...")
        
        # Listamos todos los modelos que soportan generar contenido
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ Modelo encontrado: {m.name}")
                
    except Exception as e:
        print(f"❌ Error al listar: {e}")

if __name__ == "__main__":
    listar_modelos()