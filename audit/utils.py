import uuid
from datetime import datetime, date
from decimal import Decimal
from django.db.models.fields.files import FieldFile

def safe_dict(instance):
    """
    Converts a Django model instance into a dictionary
    safe to be saved as JSON.
    """
    if not instance:
        return None

    data = {}
    
    # We traverse all model fields
    for field in instance._meta.fields:
        # We use field.attname instead of field.name to get the ID of foreign keys
        # (e.g. 'user_id' instead of trying to load the entire 'User' object)
        value = getattr(instance, field.attname)

        # Convert conflicting data types to JSON-compatible formats
        if isinstance(value, (datetime, date)):
            # Dates and times are converted to ISO text format (e.g. '2026-04-14T11:41:04')
            data[field.name] = value.isoformat()
            
        elif isinstance(value, uuid.UUID):
            # UUIDs are converted to text
            data[field.name] = str(value)
            
        elif isinstance(value, Decimal):
            # Decimals (like prices or salaries) are converted to text to not lose precision
            data[field.name] = str(value)
            
        elif isinstance(value, FieldFile):
            # If you have file or image fields, we save only the URL/path
            try:
                data[field.name] = value.url if value else None
            except ValueError:
                # This happens if the file field is empty and has no URL
                data[field.name] = None
                
        else:
            # For texts, normal numbers, booleans, etc., we leave it as is
            data[field.name] = value

    return data