import os
from dotenv import load_dotenv

try:
    from google import genai as genai_new  # SDK nuevo recomendado
except Exception:
    genai_new = None

try:
    import google.generativeai as genai_legacy  # SDK legacy (fallback)
except Exception:
    genai_legacy = None

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


def get_gemini_model_name() -> str:
    return (os.getenv("GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash").strip()


def configure_gemini():
    """
    Devuelve un dict con cliente configurado:
    - {"provider": "new", "client": <google.genai.Client>, "model": "..."}
    - {"provider": "legacy", "client": <google.generativeai module>, "model": "..."}
    """
    api_key = get_validated_gemini_api_key()
    model_name = get_gemini_model_name()

    if genai_new is not None:
        try:
            client = genai_new.Client(api_key=api_key)
            return {"provider": "new", "client": client, "model": model_name}
        except Exception:
            # Sigue al fallback legacy
            pass

    if genai_legacy is not None:
        genai_legacy.configure(api_key=api_key)
        return {"provider": "legacy", "client": genai_legacy, "model": model_name}

    raise RuntimeError(
        "No hay SDK de Gemini disponible. Instala `google-genai` o `google-generativeai`."
    )
