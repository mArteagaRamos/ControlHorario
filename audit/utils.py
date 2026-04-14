import uuid
from datetime import datetime, date
from decimal import Decimal
from django.db.models.fields.files import FieldFile

def safe_dict(instance):
    """
    Convierte una instancia de un modelo de Django en un diccionario
    seguro para ser guardado como JSON.
    """
    if not instance:
        return None

    data = {}
    
    # Recorremos todos los campos del modelo
    for field in instance._meta.fields:
        # Usamos field.attname en lugar de field.name para obtener el ID de las claves foráneas
        # (ej: 'user_id' en vez de intentar cargar el objeto 'User' entero)
        value = getattr(instance, field.attname)

        # Convertimos los tipos de datos conflictivos a formatos compatibles con JSON
        if isinstance(value, (datetime, date)):
            # Las fechas y horas se convierten a formato texto ISO (ej: '2026-04-14T11:41:04')
            data[field.name] = value.isoformat()
            
        elif isinstance(value, uuid.UUID):
            # Los UUIDs se convierten a texto
            data[field.name] = str(value)
            
        elif isinstance(value, Decimal):
            # Los decimales (como precios o salarios) se convierten a texto para no perder precisión
            data[field.name] = str(value)
            
        elif isinstance(value, FieldFile):
            # Si tienes campos de archivos o imágenes, guardamos solo la URL/ruta
            try:
                data[field.name] = value.url if value else None
            except ValueError:
                # Esto pasa si el campo de archivo está vacío y no tiene URL
                data[field.name] = None
                
        else:
            # Para textos, números normales, booleanos, etc., lo dejamos tal cual
            data[field.name] = value

    return data