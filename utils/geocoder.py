import requests
import time
import logging
from typing import Optional, Dict, Tuple
from django.core.cache import cache
import random

logger = logging.getLogger(__name__)


class OpenStreetMapGeocoder:
    """Класс для геокодирования адресов через OpenStreetMap API"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        # ВАЖНО: Добавляем пользовательский агент и реферер
        self.session.headers.update({
            'User-Agent': 'RentAnalyzerPro/1.0 (educational-project@example.com)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://rent-analyzer-pro.example.com/'
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Минимальная задержка между запросами (1 секунда)

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Геокодирование адреса с кэшированием и задержками

        Args:
            address: Адрес для геокодирования
            city: Город (опционально)

        Returns:
            Словарь с координатами или None
        """
        # Создаем ключ для кэша
        cache_key = f"geocode_{address}_{city}"

        # Пробуем получить из кэша
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Геокодирование из кэша: {address}, {city}")
            return cached_result

        # Соблюдаем задержку между запросами
        self._respect_rate_limit()

        try:
            # Формируем запрос
            query = address.strip()
            if city:
                query = f"{query}, {city}"

            # Добавляем страну для лучших результатов
            query = f"{query}, Россия"

            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'countrycodes': 'ru',
                'accept-language': 'ru',
            }

            logger.info(f"Геокодирование адреса: {query}")

            # Делаем запрос с таймаутом
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            # Проверяем статус
            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    result = data[0]
                    geocode_result = {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                        'address': result.get('address', {}),
                        'osm_id': result.get('osm_id'),
                        'osm_type': result.get('osm_type'),
                    }

                    # Сохраняем в кэш на 7 дней
                    cache.set(cache_key, geocode_result, 60 * 60 * 24 * 7)

                    logger.info(f"Успешное геокодирование: {query} → {geocode_result['lat']}, {geocode_result['lon']}")
                    return geocode_result
                else:
                    logger.warning(f"Адрес не найден: {query}")

            elif response.status_code == 403:
                logger.error(f"Доступ запрещен (403). Попробуем альтернативный метод.")
                # Пробуем без countrycodes
                return self._geocode_without_country(address, city)

            else:
                logger.error(f"Ошибка геокодирования: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при геокодировании {address}: {e}")
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга ответа для адреса {address}: {e}")

        # Если не удалось, пробуем упрощенный вариант
        return self._fallback_geocode(address, city)

    def _geocode_without_country(self, address: str, city: str = None) -> Optional[Dict]:
        """Геокодирование без ограничения по стране"""
        try:
            self._respect_rate_limit()

            query = address.strip()
            if city:
                query = f"{query}, {city}"

            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'accept-language': 'ru',
            }

            logger.info(f"Геокодирование (без countrycodes): {query}")

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result.get('display_name', ''),
                    }

        except Exception as e:
            logger.error(f"Ошибка геокодирования без страны: {e}")

        return None

    def _fallback_geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Резервный метод геокодирования - используем приблизительные координаты города
        """
        try:
            # Координаты основных городов
            city_coordinates = {
                'Москва': {'lat': 55.7558, 'lon': 37.6173},
                'Санкт-Петербург': {'lat': 59.9343, 'lon': 30.3351},
                'Екатеринбург': {'lat': 56.8389, 'lon': 60.6057},
                'Новосибирск': {'lat': 55.0084, 'lon': 82.9357},
                'Казань': {'lat': 55.8304, 'lon': 49.0661},
                'Нижний Новгород': {'lat': 56.2965, 'lon': 43.9361},
            }

            if city in city_coordinates:
                coords = city_coordinates[city]
                logger.info(f"Используем координаты города {city}: {coords['lat']}, {coords['lon']}")
                return {
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'display_name': f"{address}, {city} (приблизительно)",
                    'is_approximate': True,
                }

            # Если город не найден, используем центр России
            logger.warning(f"Город {city} не найден, используем центр России")
            return {
                'lat': 55.7558,  # Москва как центр
                'lon': 37.6173,
                'display_name': f"{address}, {city} (приблизительно)",
                'is_approximate': True,
            }

        except Exception as e:
            logger.error(f"Ошибка fallback геокодирования: {e}")
            return None

    def _respect_rate_limit(self):
        """Соблюдение ограничений по частоте запросов"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Задержка {sleep_time:.2f} сек для соблюдения rate limit")
            time.sleep(sleep_time + random.uniform(0.1, 0.5))  # Добавляем случайную задержку

        self.last_request_time = time.time()

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Обратное геокодирование: координаты -> адрес"""
        cache_key = f"reverse_geocode_{lat}_{lon}"

        # Пробуем кэш
        cached = cache.get(cache_key)
        if cached:
            return cached

        self._respect_rate_limit()

        try:
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,
                'addressdetails': 1,
                'accept-language': 'ru',
            }

            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                address = data.get('display_name', '')

                # Кэшируем на 30 дней
                cache.set(cache_key, address, 60 * 60 * 24 * 30)

                return address

        except Exception as e:
            logger.error(f"Ошибка обратного геокодирования ({lat}, {lon}): {e}")

        return None


# Создаем глобальный экземпляр
geocoder = OpenStreetMapGeocoder()