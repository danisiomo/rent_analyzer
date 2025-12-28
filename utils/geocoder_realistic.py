
import requests
import time
import logging
from typing import Optional, Dict
from django.core.cache import cache

logger = logging.getLogger(__name__)


class RealisticGeocoder:
    """Геокодер для реальных адресов"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RentAnalyzer/1.0 (educational-project@example.com)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        })
        self.last_request_time = 0
        self.min_request_interval = 1.5  # Безопасная задержка

    def _respect_rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

    def _prepare_query(self, address: str, city: str = None) -> str:
        """
        Подготовка запроса для реальных адресов

        Примеры:
        - "ул. Ленина, 50", "Екатеринбург" → "улица Ленина 50, Екатеринбург, Россия"
        - "Невский пр., 28", "Санкт-Петербург" → "Невский проспект 28, Санкт-Петербург, Россия"
        """
        # Нормализация
        address = address.strip()

        # Заменяем общеупотребительные сокращения
        replacements = [
            ('ул.', 'улица'),
            ('пр.', 'проспект'),
            ('пер.', 'переулок'),
            ('наб.', 'набережная'),
            ('пл.', 'площадь'),
            ('ш.', 'шоссе'),
            ('б-р', 'бульвар'),
            ('ал.', 'аллея'),
            ('д.', 'дом'),
            ('к.', 'квартира'),
        ]

        for short, full in replacements:
            address = address.replace(short, full)

        # Убираем лишние пробелы
        address = ' '.join(address.split())

        # Формируем итоговый запрос
        if city:
            # Убираем город из адреса если он уже есть
            city_lower = city.lower()
            address_lower = address.lower()

            if city_lower in address_lower:
                # Город уже в адресе
                query = f"{address}, Россия"
            else:
                query = f"{address}, {city}, Россия"
        else:
            query = f"{address}, Россия"

        return query

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Геокодирование реального адреса
        """
        # Подготавливаем запрос
        query = self._prepare_query(address, city)

        # Проверяем кэш
        cache_key = f"geocode_real_{address}_{city}"
        try:
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Из кэша: {address}")
                return cached
        except:
            pass

        # Соблюдаем rate limit
        self._respect_rate_limit()

        try:
            # Параметры запроса
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ru',
                'accept-language': 'ru',
            }

            logger.info(f"Запрос: {query}")

            # Отправляем запрос
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=15,
                headers={
                    'User-Agent': 'RentAnalyzer/1.0'
                }
            )

            logger.info(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    result = data[0]

                    geocode_result = {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                        'address': result.get('address', {}),
                        'query_used': query,
                    }

                    # Кэшируем
                    try:
                        cache.set(cache_key, geocode_result, 60 * 60 * 24 * 7)  # 7 дней
                    except:
                        pass

                    return geocode_result
                else:
                    logger.warning(f"Не найдено: {query}")

                    # Fallback: пробуем без номера дома
                    if any(char.isdigit() for char in address):
                        # Убираем номер дома
                        import re
                        address_no_number = re.sub(r'\s+\d+[a-zA-Zа-яА-Я]?\b', '', address)
                        if address_no_number != address:
                            logger.info(f"Пробуем без номера: {address_no_number}")
                            return self.geocode(address_no_number, city)
            else:
                logger.error(f"HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут: {query}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return None


# Глобальный экземпляр
geocoder = RealisticGeocoder()