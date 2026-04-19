import os
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    genai = None

load_dotenv()


def normalize_api_key(raw_key: str) -> str:
    cleaned = (raw_key or "").strip().strip('"').strip("'")
    cleaned = cleaned.replace("\ufeff", "")
    if cleaned.lower().startswith("api_key="):
        cleaned = cleaned.split("=", 1)[1].strip()
    return cleaned


def get_validated_gemini_api_key() -> str:
    api_key = normalize_api_key(os.getenv("GEMINI_API_KEY", ""))

    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en variables de entorno.")
    if api_key.isdigit():
        raise RuntimeError(
            "GEMINI_API_KEY inválida: parece un número/Project ID, no una API key real de Google AI Studio."
        )
    if not api_key.startswith("AIza"):
        raise RuntimeError(
            "GEMINI_API_KEY inválida: debe iniciar con 'AIza'. Revisa tu .env."
        )
    return api_key


def configure_gemini():
    if genai is None:
        raise RuntimeError(
            "La librería google.generativeai no está instalada o no pudo importarse."
        )

    api_key = get_validated_gemini_api_key()
    genai.configure(api_key=api_key)
    return genai
