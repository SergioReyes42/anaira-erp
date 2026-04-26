import io
import json
import base64
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from core.gemini_config import configure_gemini


def _safe_fallback(error_message="Hubo un error al leer la imagen"):
    return {
        "provider_name": "Error de Lectura IA",
        "provider_nit": "",
        "invoice_series": "",
        "invoice_number": "",
        "total": 0.00,
        "is_fuel": False,
        "fuel_type": "",
        "description": error_message,
        "account_type": "Gastos Generales"
    }


def _configure_gemini():
    return configure_gemini()


def normalize_scanner_image(uploaded_file, max_side=2200, quality=82):
    """
    Normaliza imagen para scanner:
    - corrige orientación EXIF
    - convierte a RGB
    - comprime JPEG
    """
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    img.thumbnail((max_side, max_side), Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)
    return ContentFile(output.read())


def build_scanner_expense_payload(user, company, vehicle_obj, smart_input="", include_storage_flag=False):
    """
    Construye payload base para Expense del scanner sin IA.
    """
    description_base = (smart_input or "Factura subida por scanner (sin IA)")
    if include_storage_flag:
        description_base = f"{description_base} [SIN_IMAGEN: revisar storage]"

    return {
        "user": user,
        "company": company,
        "vehicle": vehicle_obj,
        "provider_name": "Pendiente de revisión",
        "provider_nit": "C/F",
        "invoice_series": "",
        "invoice_number": "",
        "description": description_base[:255],
        "suggested_account": "Gastos Generales",
        "total_amount": 0.00,
        "tax_base": 0.00,
        "tax_iva": 0.00,
        "tax_idp": 0.00,
        "status": "PENDING",
        "origin": "SCANNER",
    }


def _extract_text_from_genai_response(response):
    # 1) Camino directo
    text = (getattr(response, "text", None) or "").strip()
    if text:
        return text

    # 2) Camino por candidatos/partes (SDK nuevo)
    try:
        candidates = getattr(response, "candidates", None) or []
        chunks = []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    chunks.append(t)
        text = "\n".join(chunks).strip()
        if text:
            return text
    except Exception:
        pass

    return ""


def _extract_json_block(raw_text: str) -> str:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return ""

    # Si viene limpio, úsalo.
    if raw_text.startswith("{") and raw_text.endswith("}"):
        return raw_text

    # Si viene dentro de markdown ```json ... ```
    if "```" in raw_text:
        parts = raw_text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                return part

    # fallback por llaves
    s = raw_text.find("{")
    e = raw_text.rfind("}")
    if s != -1 and e != -1 and e > s:
        return raw_text[s:e + 1]

    return raw_text


def analyze_invoice_image(image_file, smart_input=""):
    """
    Cerebro IA Francotirador: Analiza facturas con reglas SAT Guatemala.
    """
    try:
        cfg = _configure_gemini()

        prompt = f"""
        Eres un Auditor Fiscal Experto de la SAT en Guatemala.
        Tu misión es extraer los datos exactos de esta factura electrónica (FEL) o recibo.
        
        REGLAS DE ORO (Si rompes una, el sistema falla):
        1. CERO INVENTOS: Si un dato no es visible, legible o no existe, devuelve exactamente null. La imagen puede estar rotada, ajusta tu lectura.
        2. TOTAL: Busca "TOTAL", "Q.", "GTQ". Devuelve SOLO el número final (ej. 150.50).
        3. NIT: Extrae el NIT del emisor. Mantenlo con su guion si lo tiene (ej. 123456-7).
        4. DTE/SERIE: Las FEL guatemaltecas tienen Serie (ej. 8A1B2C3D o A) y Número de autorización. Extrae ambos.
        5. COMBUSTIBLE: Si ves "Galones", "Diesel", "Super", "Regular", o es una gasolinera (Shell, Puma, Texaco, Uno), is_fuel debe ser true obligatoriamente.
        
        CATÁLOGO DE CUENTAS (Debes elegir estrictamente UNA):
        - "Combustibles y Lubricantes"
        - "Mantenimiento y Reparación de Vehículos"
        - "Papelería y Útiles de Oficina"
        - "Atenciones al Personal y Clientes"
        - "Servicios Públicos y Telefonía"
        - "Mobiliario y Equipo de Computo"
        - "Inventario de Mercadería"
        - "Gastos Generales"

        Contexto adicional del contador: {smart_input}

        Devuelve el resultado estrictamente en este esquema JSON:
        {{
            "provider_name": "Nombre completo de la empresa",
            "provider_nit": "NIT del emisor",
            "invoice_series": "Serie de la factura",
            "invoice_number": "Número de factura o DTE",
            "total": 0.00,
            "is_fuel": true o false,
            "fuel_type": "regular, diesel, super o null",
            "description": "Qué se compró (máximo 5 palabras)",
            "account_type": "CUENTA_EXACTA_DEL_CATALOGO"
        }}
        """

        model_candidates = cfg.get("model_candidates") or [cfg["model"]]
        last_err = None
        raw_text = ""

        for model_name in model_candidates:
            try:
                # SDK nuevo google.genai (único)
                image_file.seek(0)
                image_bytes = image_file.read()
                encoded = base64.b64encode(image_bytes).decode("utf-8")

                response = cfg["client"].models.generate_content(
                    model=model_name,
                    contents=[
                        {"role": "user", "parts": [{"text": prompt}]},
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": encoded
                                    }
                                }
                            ],
                        },
                    ],
                )
                raw_text = _extract_text_from_genai_response(response)

                if raw_text:
                    break
            except Exception as model_err:
                last_err = model_err
                continue

        if not raw_text:
            if last_err is not None:
                raise RuntimeError(f"Gemini sin respuesta utilizable. Último error: {last_err}")
            raise RuntimeError("Gemini no devolvió texto utilizable.")

        json_text = _extract_json_block(raw_text)
        data = json.loads(json_text)

        data["total"] = float(data.get("total") or 0.00)
        data["provider_name"] = data.get("provider_name") or "Proveedor no detectado"
        data["account_type"] = data.get("account_type") or "Gastos Generales"
        data["is_fuel"] = bool(data.get("is_fuel"))

        return data

    except Exception as e:
        print(f"🔥 Error Crítico en IA (Smart Scanner): {e}")
        return _safe_fallback(str(e))
