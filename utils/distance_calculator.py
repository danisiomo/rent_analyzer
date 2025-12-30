import math
from typing import Optional


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Конвертируем градусы в радианы
    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    # Радиус Земли в километрах
    R = 6371.0

    # Разницы координат
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Формула гаверсинусов
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def filter_by_distance(offers, center_lat: float, center_lon: float, max_distance_km: float):
    filtered = []

    for offer in offers:
        if offer.latitude and offer.longitude:
            distance = calculate_distance(
                center_lat, center_lon,
                float(offer.latitude), float(offer.longitude)
            )
            offer.distance_km = round(distance, 1)

            if distance <= max_distance_km:
                filtered.append(offer)
        else:
            # Если нет координатов, все равно добавляем
            offer.distance_km = None
            filtered.append(offer)

    return filtered