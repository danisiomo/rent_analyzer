import requests
import time
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SimpleWorkingGeocoder:
    """Самый простой рабочий геокодер"""

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        # Форматируем адрес: "ул. Садовая, 4" -> "улица Садовая 4"
        address = address.strip()

        # Простые замены
        address = address.replace('ул.', 'улица')
        address = address.replace('пр.', 'проспект')

        # Убираем запятую между улицей и номером
        if ', ' in address:
            parts = address.split(', ')
            if len(parts) == 2 and parts[1].isdigit():
                address = f"{parts[0]} {parts[1]}"

        # Формируем запрос
        if city:
            query = f"{address}, {city}, Россия"
        else:
            query = f"{address}, Россия"

        logger.info(f"Запрос: {query}")

        try:
            # ТОЧНО такой же запрос как в работающем тесте
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'ru',
                },
                headers={
                    'User-Agent': 'RentAnalyzerPro/1.0'  # ВАЖНО: тот же User-Agent
                },
                timeout=10  # ВАЖНО: тот же таймаут
            )

            logger.info(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data:
                    result = data[0]
                    return {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                    }
            else:
                logger.error(f"Ошибка {response.status_code}")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return None


# Глобальный экземпляр
geocoder = SimpleWorkingGeocoder()