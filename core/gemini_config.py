import os
from dotenv import load_dotenv

try:
    from google import genai as genai_new  # SDK nuevo recomendado
except Exception:
    genai_new = None

# Legacy SDK desactivado intencionalmente para evitar rutas v1beta incompatibles.
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


def get_gemini_model_candidates():
    primary = get_gemini_model_name()
    fallbacks = [
        primary,
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ]
    unique = []
    for m in fallbacks:
        if m and m not in unique:
            unique.append(m)
    return unique


def configure_gemini():
    """
    Devuelve cliente del SDK nuevo únicamente:
    - {"provider": "new", "client": <google.genai.Client>, "model": "..."}
    """
    api_key = get_validated_gemini_api_key()
    model_name = get_gemini_model_name()

    if genai_new is None:
        raise RuntimeError(
            "SDK google.genai no disponible. Instala/actualiza dependencia `google-genai`."
        )

    try:
        client = genai_new.Client(api_key=api_key)
        return {
            "provider": "new",
            "client": client,
            "model": model_name,
            "model_candidates": get_gemini_model_candidates(),
        }
    except Exception as e:
        raise RuntimeError(f"No se pudo inicializar google.genai: {e}")
