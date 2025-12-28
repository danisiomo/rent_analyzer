# utils/geocoder_simple.py
import requests
import time
import logging
from typing import Optional, Dict
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleNominatimGeocoder:
    """Простой геокодировщик без зависимостей от Django"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RentAnalyzerPro-Test/1.0 (educational-test@example.com)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        })
        self.last_request_time = 0
        self.min_request_interval = 1.5  # Безопасная задержка

    def _respect_rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _clean_address(self, address: str) -> str:
        """Очистка адреса"""
        if not address:
            return ""

        # Простая нормализация
        address = ' '.join(address.strip().split())
        replacements = {
            ' ул. ': ' улица ',
            ' пр. ': ' проспект ',
            ' д. ': ' дом ',
        }

        for old, new in replacements.items():
            address = address.replace(old, new)

        return ' '.join(address.split())

    def geocode_simple(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Простое геокодирование - используем только свободный поиск
        """
        self._respect_rate_limit()

        try:
            # Очищаем адрес
            address_clean = self._clean_address(address)

            # Формируем запрос
            query = address_clean
            if city:
                query = f"{query}, {city}"
            query = f"{query}, Россия"

            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'countrycodes': 'ru',
                'accept-language': 'ru',
            }

            logger.info(f"Запрос: {query}")

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    result = data[0]
                    return {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                        'address': result.get('address', {}),
                    }
                else:
                    logger.warning(f"Не найдено: {query}")
            else:
                logger.error(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return None

    def geocode_structured(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Структурированное геокодирование (более точное)
        """
        self._respect_rate_limit()

        try:
            # Парсим адрес
            address_clean = self._clean_address(address)

            # Пробуем извлечь улицу и номер дома
            match = re.search(r'(.+?)\s+(\d+[a-zA-Zа-яА-Я]?)$', address_clean)

            params = {
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'countrycodes': 'ru',
                'accept-language': 'ru',
            }

            if match:
                # Есть улица и номер
                street_name = match.group(1).strip()
                house_number = match.group(2).strip()

                params['street'] = f"{street_name} {house_number}"
                params['housenumber'] = house_number

                if city:
                    params['city'] = city

                logger.info(f"Структурированный запрос: street={params.get('street')}, city={params.get('city')}")
            else:
                # Нет номера, используем свободный поиск
                query = address_clean
                if city:
                    query = f"{query}, {city}"
                params['q'] = f"{query}, Россия"
                logger.info(f"Свободный запрос: {params['q']}")

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    result = data[0]
                    return {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                        'address': result.get('address', {}),
                        'params_used': params,
                    }

        except Exception as e:
            logger.error(f"Ошибка структурированного поиска: {e}")

        return None


# Создаем глобальный экземпляр
simple_geocoder = SimpleNominatimGeocoder()