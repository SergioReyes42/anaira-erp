# core/ai_brain.py
import random
from datetime import date

def analizar_documento_ia(imagen, contexto=None):
    """
    Simula el procesamiento de IA.
    1. Intenta detectar por nombre de archivo.
    2. Si falla, usa el 'contexto' (IN/OUT) para deducir el tipo.
    """
    nombre_archivo = imagen.name.lower()
    resultado = {
        'exito': True, # Somos optimistas por defecto para la Demo
        'tipo_detectado': 'GENERICO',
        'datos': {}
    }

    # --- LÓGICA DE DETECCIÓN ---
    es_cheque = 'cheque' in nombre_archivo or (contexto == 'OUT' and 'deposito' not in nombre_archivo)
    es_deposito = 'deposito' in nombre_archivo or 'boleta' in nombre_archivo or (contexto == 'IN' and 'cheque' not in nombre_archivo)
    es_factura = 'factura' in nombre_archivo or 'gasto' in nombre_archivo

    # 1. CASO CHEQUE (Salidas)
    if es_cheque:
        resultado['tipo_detectado'] = 'CHEQUE'
        resultado['datos'] = {
            'monto': round(random.uniform(1000, 5000), 2),
            'banco_emisor': 'Banrural',
            'numero_cheque': str(random.randint(100000, 999999)),
            'beneficiario': 'Portador',
            'fecha': date.today()
        }

    # 2. CASO DEPÓSITO (Entradas)
    elif es_deposito:
        resultado['tipo_detectado'] = 'DEPOSITO'
        resultado['datos'] = {
            'monto': round(random.uniform(500, 2500), 2),
            'banco_receptor': 'Banco Industrial',
            'no_boleta': str(random.randint(444000, 888000)),
            'depositante': 'Cliente Mostrador',
            'fecha': date.today()
        }

    # 3. CASO FACTURA (Gastos)
    elif es_factura:
        resultado['tipo_detectado'] = 'FACTURA'
        resultado['datos'] = {
            'total': round(random.uniform(100, 800), 2),
            'proveedor': 'Gasolinera La Torre',
            'nit': 'CF',
            'serie': 'FEL-1',
            'es_combustible': True
        }
    
    else:
        # Si todo falla, devolvemos un genérico para no dar error
        resultado['tipo_detectado'] = 'DOCUMENTO'
        resultado['datos'] = {
            'monto': 0.00,
            'description': 'No se pudo leer el texto claro',
            'fecha': date.today()
        }

    return resultado