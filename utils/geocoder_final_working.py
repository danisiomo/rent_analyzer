import requests
import time
import logging
from typing import Optional, Dict
from django.core.cache import cache

logger = logging.getLogger(__name__)


class WorkingGeocoder:
    """Рабочий геокодировщик на основе теста, который работает"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        # ВАЖНО: Используем тот же User-Agent, что и в работающем тесте
        self.session.headers.update({
            'User-Agent': 'RentAnalyzerPro/1.0',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 секунда между запросами

    def _respect_rate_limit(self):
        """Соблюдение rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

    def _format_address_for_nominatim(self, address: str, city: str = None) -> str:
        """
        Форматируем адрес для Nominatim

        Из 'ул. Садовая, 4' делаем 'улица Садовая 4'
        """
        # Сначала нормализуем адрес
        address = address.strip()

        # Заменяем сокращения
        replacements = {
            'ул.': 'улица',
            'пр.': 'проспект',
            'пер.': 'переулок',
            'наб.': 'набережная',
            'пл.': 'площадь',
            'ш.': 'шоссе',
            'б-р': 'бульвар',
            'ал.': 'аллея',
        }

        # Простая замена в строке
        for short, full in replacements.items():
            # Заменяем только если это отдельное слово
            address = address.replace(f' {short} ', f' {full} ')
            if address.startswith(f'{short} '):
                address = address.replace(f'{short} ', f'{full} ', 1)

        # Убираем запятые между улицей и номером
        # 'улица Садовая, 4' -> 'улица Садовая 4'
        import re
        address = re.sub(r'(\D+),\s*(\d+)', r'\1 \2', address)

        # Если указан город, добавляем его
        if city:
            # Убираем город из адреса, если он уже есть
            city_lower = city.lower()
            address_lower = address.lower()

            # Если адрес начинается с города, убираем его
            if address_lower.startswith(city_lower + ', '):
                address = address[len(city) + 2:]
            elif address_lower.startswith(city_lower + ' '):
                address = address[len(city) + 1:]

            return f"{address}, {city}, Россия"
        else:
            return f"{address}, Россия"

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Геокодирование - точная копия работающего теста
        """
        # Форматируем адрес
        formatted_address = self._format_address_for_nominatim(address, city)

        # Кэширование
        cache_key = f"geocode_working_{address}_{city}"
        try:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Из кэша: {formatted_address}")
                return cached_result
        except:
            pass

        # Соблюдаем rate limit
        self._respect_rate_limit()

        try:
            # Параметры как в работающем тесте
            params = {
                'q': formatted_address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ru',
            }

            logger.info(f"Запрос Nominatim: {formatted_address}")

            # Запрос с таймаутом как в тесте
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10,  # ТАКОЙ ЖЕ ТАЙМАУТ КАК В РАБОТАЮЩЕМ ТЕСТЕ
                headers={
                    'User-Agent': 'RentAnalyzerPro/1.0'  # ТАКОЙ ЖЕ User-Agent
                }
            )

            logger.info(f"Ответ Nominatim: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    result = data[0]

                    geocode_result = {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                        'address': result.get('address', {}),
                        'query_used': formatted_address,
                    }

                    # Кэшируем
                    try:
                        cache.set(cache_key, geocode_result, 60 * 60 * 24)
                    except:
                        pass

                    logger.info(f"Успешно: {geocode_result['lat']}, {geocode_result['lon']}")
                    return geocode_result
                else:
                    logger.warning(f"Не найдено: {formatted_address}")
            else:
                logger.error(f"Ошибка HTTP {response.status_code}: {response.text[:200]}")

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут для: {formatted_address}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return None

    def geocode_structured(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Структурированное геокодирование (второй вариант из теста)
        """
        self._respect_rate_limit()

        try:
            # Парсим адрес для структурированного запроса
            formatted_address = self._format_address_for_nominatim(address, city)

            # Извлекаем улицу и номер
            import re
            match = re.search(r'(.+?)\s+(\d+[a-zA-Zа-яА-Я]?)$', formatted_address.split(',')[0])

            params = {
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ru',
            }

            if match and city:
                # Структурированный запрос
                street = match.group(1).strip()
                housenumber = match.group(2).strip()

                params['street'] = f"{street} {housenumber}"
                params['city'] = city
                params['country'] = 'Россия'

                logger.info(f"Структурированный: street={params['street']}, city={city}")
            else:
                # Обычный запрос
                params['q'] = formatted_address

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10,
                headers={'User-Agent': 'RentAnalyzerPro/1.0'}
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    result = data[0]
                    return {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                    }

        except Exception as e:
            logger.error(f"Ошибка структурированного: {e}")

        return None


# Глобальный экземпляр
geocoder = WorkingGeocoder()