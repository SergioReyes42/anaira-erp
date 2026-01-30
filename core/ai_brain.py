# core/ai_brain.py
import random
from datetime import date

def analizar_documento_ia(imagen):
    """
    Simula el procesamiento de Inteligencia Artificial (OCR).
    En el futuro, aquí conectaremos Google Vision o AWS Textract.
    
    Retorna un diccionario con los datos extraídos.
    """
    nombre_archivo = imagen.name.lower()
    resultado = {
        'exito': True,
        'tipo_detectado': 'DESCONOCIDO',
        'datos': {}
    }

    # 1. Lógica para detectar CHEQUES
    if 'cheque' in nombre_archivo:
        resultado['tipo_detectado'] = 'CHEQUE'
        resultado['datos'] = {
            'monto': round(random.uniform(1000, 5000), 2),
            'banco_emisor': 'Banrural',
            'numero_cheque': str(random.randint(100000, 999999)),
            'beneficiario': 'Grupo Transfer S.A.',
            'fecha': date.today()
        }

    # 2. Lógica para detectar BOLETAS DE DEPÓSITO
    elif 'deposito' in nombre_archivo or 'boleta' in nombre_archivo:
        resultado['tipo_detectado'] = 'DEPOSITO'
        resultado['datos'] = {
            'monto': round(random.uniform(500, 2000), 2),
            'banco_receptor': 'Banco Industrial',
            'no_boleta': str(random.randint(444000, 888000)),
            'depositante': 'Cliente Frecuente',
            'fecha': date.today()
        }

    # 3. Lógica para detectar FACTURAS (Gastos)
    elif 'factura' in nombre_archivo or 'gasto' in nombre_archivo:
        resultado['tipo_detectado'] = 'FACTURA'
        resultado['datos'] = {
            'total': round(random.uniform(100, 800), 2),
            'proveedor': 'Gasolinera Shell',
            'nit': '123456-K',
            'serie': 'FACE-66',
            'es_combustible': True
        }
    
    else:
        resultado['exito'] = False
        resultado['mensaje'] = "No se pudo identificar el tipo de documento. Intente con una imagen más clara."

    return resultado