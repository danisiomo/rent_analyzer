import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """Кастомный JSON encoder для обработки Decimal объектов"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        # Для других типов используем стандартный encoder
        return super(DecimalEncoder, self).default(obj)


def decimal_to_float(data):
    """Рекурсивно конвертирует Decimal в float в словаре"""
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_float(v) for v in data]
    else:
        return data