# core/ai_brain.py
import json
from datetime import date
import datetime
import logging
import re  # <--- AGREGADO: Importante para la función de texto
import decimal
from django.db.models import Sum
from accounting.models import Expense, JournalEntryLine, Supplier, Account
from core.gemini_config import configure_gemini

# Configuración del modelo (GEMINI)
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 8192,
}

try:
    genai = configure_gemini()
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )
except Exception:
    genai = None
    model = None

def analizar_documento_ia(imagen, contexto=None):
    resultado = {'exito': False, 'tipo_detectado': 'DESCONOCIDO', 'datos': {}}

    try:
        if model is None:
            raise RuntimeError("Gemini no disponible. Verifica GEMINI_API_KEY válida en entorno.")

        img_bytes = imagen.read()
        
        prompt_base = "Eres un asistente experto en ERP. Analiza la imagen y extrae datos en JSON estricto."

        if contexto == 'GASTO':
            prompt_especifico = """Contexto: FACTURA COMPRA. Extrae: "proveedor", "total", "fecha", "serie", "nit"."""
        
        elif contexto == 'IN':
            prompt_especifico = """Contexto: BOLETA DEPOSITO. Extrae: "monto", "no_boleta", "fecha"."""
            
        elif contexto == 'OUT':
            prompt_especifico = """Contexto: CHEQUE. Extrae: "monto", "numero_cheque", "beneficiario", "fecha"."""
            
        elif contexto == 'COTIZACION':
            prompt_especifico = """Contexto: PEDIDO CLIENTE. Extrae: "cliente", "productos" (array), "observaciones"."""
        
        # --- NUEVO: CONTEXTO PRODUCTO ---
        elif contexto == 'PRODUCTO':
            prompt_especifico = """
            Contexto: ETIQUETA O CAJA DE PRODUCTO.
            Extrae:
            - "nombre": Nombre comercial del producto.
            - "descripcion": Características clave (peso, tamaño, modelo).
            - "marca": Marca del fabricante.
            - "codigo": Si ves un código de barras o SKU escríbelo.
            """
        else:
            prompt_especifico = "Extrae datos generales."

        full_prompt = prompt_base + prompt_especifico

        response = model.generate_content([{'mime_type': imagen.content_type, 'data': img_bytes}, full_prompt])
        
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        datos_json = json.loads(texto_limpio)
        
        resultado['exito'] = True
        resultado['datos'] = datos_json
        
    except Exception as e:
        print(f"Error IA: {e}")
        resultado['mensaje'] = str(e)

    imagen.seek(0)
    return resultado

# --- FUNCIÓN 2: PARA TEXTO (Regex) ---
def responder_chat_contable(pregunta, contexto_empresa=None):
    """
    Fase 1: Chat IA contable para consultas del ERP.
    - Solo respuesta textual (sin acciones transaccionales).
    - Usa Gemini si está disponible, con fallback seguro.
    """
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"ok": False, "respuesta": "La pregunta está vacía."}

    empresa_txt = f"Empresa actual: {contexto_empresa}" if contexto_empresa else "Empresa actual no especificada"

    if model is None:
        return {
            "ok": True,
            "respuesta": (
                "IA no disponible temporalmente. "
                "Puedo ayudarte con guías contables básicas: clasificaciones NIIF, estructura Debe/Haber "
                "y criterios para separar combustible sin placa."
            ),
        }

    prompt = f"""
Eres ANAIRA IA CONTABLE, asistente experto en contabilidad para ERP.
Responde en español, de forma clara y profesional.

Reglas:
- Prioriza respuesta útil y práctica para operación contable.
- Si preguntan por reportes de flotilla: recordar que gastos SIN placa no deben afectar reporte por vehículo.
- Si no hay datos suficientes, solicita concretar rango/criterio.
- No inventes cifras del sistema; indica que se requiere consulta de datos reales si aplica.

Contexto:
{empresa_txt}

Pregunta del usuario:
{pregunta}
""".strip()

    try:
        response = model.generate_content(prompt)
        texto = (response.text or "").strip()
        if not texto:
            texto = "No pude generar respuesta en este momento. Intenta reformular la pregunta."
        return {"ok": True, "respuesta": texto}
    except Exception as e:
        logging.exception("Fallo en responder_chat_contable")
        return {
            "ok": True,
            "respuesta": f"Ocurrió un problema temporal al consultar IA: {str(e)}",
        }


def _parse_date_or_none(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _detectar_tool_contable(pregunta):
    q = (pregunta or "").lower()

    if any(k in q for k in ["gasto", "gastos", "combustible", "mantenimiento", "repuesto"]):
        return "buscar_gastos"
    if any(k in q for k in ["libro diario", "diario", "debe", "haber", "partida"]):
        return "resumen_libro_diario"
    if any(k in q for k in ["proveedor", "proveedores", "supplier"]):
        return "buscar_proveedores"
    if any(k in q for k in ["borrador", "asiento manual", "partida manual", "crear partida"]):
        return "borrador_partida_manual"
    return "chat_general"


def tool_buscar_gastos(company, payload):
    qs = Expense.objects.filter(company=company).order_by('-date')
    fecha_inicio = _parse_date_or_none(payload.get('fecha_inicio', ''))
    fecha_fin = _parse_date_or_none(payload.get('fecha_fin', ''))

    if fecha_inicio:
        qs = qs.filter(date__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(date__date__lte=fecha_fin)

    top = min(int(payload.get('top', 10) or 10), 50)
    items = []
    for g in qs[:top]:
        items.append({
            "id": g.id,
            "fecha": g.date.strftime("%Y-%m-%d"),
            "tipo": getattr(g, 'tipo_gasto', ''),
            "proveedor": getattr(g, 'provider_name', ''),
            "descripcion": getattr(g, 'description', ''),
            "monto": float(getattr(g, 'total_amount', 0) or 0),
            "estado": getattr(g, 'status', ''),
        })

    total = qs.aggregate(total=Sum('total_amount'))['total'] or decimal.Decimal('0')
    return {
        "ok": True,
        "tool": "buscar_gastos",
        "resumen": f"Se encontraron {qs.count()} gastos. Total: Q {total}",
        "data": items,
    }


def tool_resumen_libro_diario(company, payload):
    fecha_inicio = _parse_date_or_none(payload.get('fecha_inicio', ''))
    fecha_fin = _parse_date_or_none(payload.get('fecha_fin', ''))
    lineas = JournalEntryLine.objects.filter(entry__company=str(company.id))

    if fecha_inicio:
        lineas = lineas.filter(entry__date__gte=fecha_inicio)
    if fecha_fin:
        lineas = lineas.filter(entry__date__lte=fecha_fin)

    total_debe = lineas.aggregate(total=Sum('debit'))['total'] or decimal.Decimal('0')
    total_haber = lineas.aggregate(total=Sum('credit'))['total'] or decimal.Decimal('0')

    return {
        "ok": True,
        "tool": "resumen_libro_diario",
        "resumen": f"Totales del período -> Debe: Q {total_debe} / Haber: Q {total_haber}",
        "data": {
            "total_debe": float(total_debe),
            "total_haber": float(total_haber),
            "cuadra": bool(total_debe == total_haber),
        }
    }


def tool_buscar_proveedores(company, payload):
    termino = (payload.get('termino') or '').strip()
    qs = Supplier.objects.filter(company=company)
    if termino:
        qs = qs.filter(name__icontains=termino)

    items = [{"id": s.id, "name": s.name, "nit": s.nit, "phone": s.phone} for s in qs[:50]]
    return {
        "ok": True,
        "tool": "buscar_proveedores",
        "resumen": f"Proveedores encontrados: {qs.count()}",
        "data": items
    }


def tool_borrador_partida_manual(company, payload):
    lineas = payload.get('lineas') or []
    concepto = (payload.get('concepto') or '').strip()

    if not concepto:
        return {"ok": False, "tool": "borrador_partida_manual", "error": "Falta concepto."}
    if not isinstance(lineas, list) or not lineas:
        return {"ok": False, "tool": "borrador_partida_manual", "error": "Debes enviar líneas contables."}

    total_debe = decimal.Decimal('0')
    total_haber = decimal.Decimal('0')
    normalizadas = []

    for i, ln in enumerate(lineas, start=1):
        account_id = ln.get('account_id')
        debit = decimal.Decimal(str(ln.get('debit', 0) or 0))
        credit = decimal.Decimal(str(ln.get('credit', 0) or 0))

        if debit < 0 or credit < 0:
            return {"ok": False, "tool": "borrador_partida_manual", "error": f"Línea {i} contiene negativos."}
        if debit > 0 and credit > 0:
            return {"ok": False, "tool": "borrador_partida_manual", "error": f"Línea {i} tiene Debe y Haber al mismo tiempo."}
        if debit == 0 and credit == 0:
            continue

        cuenta = Account.objects.filter(id=account_id, is_transactional=True).first()
        if not cuenta:
            return {"ok": False, "tool": "borrador_partida_manual", "error": f"Cuenta inválida en línea {i}."}

        total_debe += debit
        total_haber += credit
        normalizadas.append({
            "account_id": cuenta.id,
            "account_code": cuenta.code,
            "account_name": cuenta.name,
            "debit": float(debit),
            "credit": float(credit),
        })

    if not normalizadas:
        return {"ok": False, "tool": "borrador_partida_manual", "error": "No hay líneas válidas."}
    if total_debe != total_haber:
        return {
            "ok": False,
            "tool": "borrador_partida_manual",
            "error": f"La partida no cuadra. Debe: {total_debe} / Haber: {total_haber}"
        }

    return {
        "ok": True,
        "tool": "borrador_partida_manual",
        "resumen": "Borrador generado correctamente. Partida cuadrada.",
        "data": {
            "concepto": concepto,
            "total_debe": float(total_debe),
            "total_haber": float(total_haber),
            "lineas": normalizadas
        }
    }


def ejecutar_tool_contable(pregunta, company, payload=None):
    payload = payload or {}
    tool = payload.get('tool') or _detectar_tool_contable(pregunta)

    if tool == "buscar_gastos":
        return tool_buscar_gastos(company, payload)
    if tool == "resumen_libro_diario":
        return tool_resumen_libro_diario(company, payload)
    if tool == "buscar_proveedores":
        return tool_buscar_proveedores(company, payload)
    if tool == "borrador_partida_manual":
        return tool_borrador_partida_manual(company, payload)

    return {
        "ok": True,
        "tool": "chat_general",
        "resumen": responder_chat_contable(pregunta, contexto_empresa=getattr(company, 'name', None)).get("respuesta", ""),
        "data": {}
    }


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