import requests
import time
from typing import Optional, Dict, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class OpenStreetMapGeocoder:
    """Класс для геокодирования адресов через OpenStreetMap API"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"
    DETAILS_URL = "https://nominatim.openstreetmap.org/details"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RentAnalyzerPro/1.0 (daniil@example.com)'
        })

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Геокодирование адреса
        Возвращает координаты и дополнительную информацию
        """
        try:
            # Формируем запрос
            query = address
            if city:
                query = f"{address}, {city}"

            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'countrycodes': 'ru',  # Ограничиваем поиск Россией
            }

            logger.info(f"Geocoding address: {query}")

            # Делаем запрос
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()

            if data:
                result = data[0]
                return {
                    'lat': float(result['lat']),
                    'lon': float(result['lon']),
                    'display_name': result.get('display_name', ''),
                    'address': result.get('address', {}),
                    'osm_id': result.get('osm_id'),
                    'osm_type': result.get('osm_type'),
                }

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding error for address {address}: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Data parsing error for address {address}: {e}")
            return None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Обратное геокодирование: координаты -> адрес"""
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,  # Детальный уровень
            }

            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()

            if data and 'display_name' in data:
                return data['display_name']

            return None

        except Exception as e:
            logger.error(f"Reverse geocoding error for ({lat}, {lon}): {e}")
            return None

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Расчет расстояния между двумя точками (упрощенная формула)
        Возвращает расстояние в километрах
        """
        from math import radians, sin, cos, sqrt, atan2

        # Конвертируем градусы в радианы
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Разницы координат
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Формула гаверсинусов
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Радиус Земли в километрах
        R = 6371.0

        return R * c


# Создаем глобальный экземпляр для использования в проекте
geocoder = OpenStreetMapGeocoder()