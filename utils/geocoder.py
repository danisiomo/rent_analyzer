import re

import requests
import time
import logging
from typing import Optional, Dict, Tuple
from django.core.cache import cache
import random
import math
logger = logging.getLogger(__name__)


class OpenStreetMapGeocoder:
    """Класс для геокодирования адресов через OpenStreetMap API"""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        # Добавляем пользовательский агент и реферер
        self.session.headers.update({
            'User-Agent': 'RentAnalyzerPro/1.0 (educational-project@example.com)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://rent-analyzer-pro.example.com/'
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Минимальная задержка между запросами (1 секунда)

    def normalize_address(self, address: str) -> str:
        """
        Нормализация адреса для лучшего поиска
        """
        # Убираем лишние пробелы
        address = ' '.join(address.strip().split())

        # Стандартизируем сокращения (только если отдельно стоят)
        replacements = [
            (' пр-кт ', ' проспект '),
            (' пр. ', ' проспект '),
            (' ул. ', ' улица '),
            (' пер. ', ' переулок '),
            (' наб. ', ' набережная '),
            (' пл. ', ' площадь '),
            (' ш. ', ' шоссе '),
            (' бул. ', ' бульвар '),
            (' пр-д ', ' проезд '),
            (' ал. ', ' аллея '),
            (' б-р ', ' бульвар '),
        ]

        for old, new in replacements:
            address = address.replace(old, new)

        # Убираем двойные пробелы
        address = ' '.join(address.split())

        return address

    def extract_address_parts(self, address: str):
        """
        Извлекает части адреса для формирования разных вариантов запроса
        """
        address_lower = address.lower()

        # Удаляем город из начала адреса, если он есть
        cities = ['санкт-петербург', 'москва', 'екатеринбург', 'новосибирск', 'казань']
        for city in cities:
            if address_lower.startswith(city):
                # Оставляем только часть после города и запятой
                parts = address.split(',', 1)
                if len(parts) > 1:
                    address = parts[1].strip()
                break

        # Разделяем по запятым
        parts = [part.strip() for part in address.split(',')]

        # Если есть как минимум 3 части (район, улица, дом)
        if len(parts) >= 3:
            return {
                'full': address,
                'district_street': f"{parts[-2]}, {parts[-1]}",  # район, улица+дом
                'street_only': parts[-1],  # только улица+дом
                'street_without_number': ' '.join(parts[-1].split()[:-1]) if len(parts[-1].split()) > 1 else parts[-1],
            }
        elif len(parts) == 2:
            return {
                'full': address,
                'street_only': parts[-1],
                'street_without_number': ' '.join(parts[-1].split()[:-1]) if len(parts[-1].split()) > 1 else parts[-1],
            }
        else:
            return {
                'full': address,
                'street_only': address,
                'street_without_number': ' '.join(address.split()[:-1]) if len(address.split()) > 1 else address,
            }

    def geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Геокодирование адреса с кэшированием и задержками
        """
        # Нормализуем адрес
        normalized_address = self.normalize_address(address)
        logger.info(f"Нормализованный адрес: '{address}' -> '{normalized_address}'")

        # Если city не указан, пробуем извлечь из адреса
        if not city:
            # Пробуем найти город в адресе
            address_lower = normalized_address.lower()
            city_patterns = {
                'санкт-петербург': ['санкт-петербург', 'спб', 'петербург'],
                'москва': ['москва', 'г. москва'],
            }

            for city_name, patterns in city_patterns.items():
                for pattern in patterns:
                    if pattern in address_lower:
                        city = city_name
                        logger.info(f"Город извлечен из адреса: {city}")
                        break
                if city:
                    break

        # Извлекаем части адреса для разных вариантов запроса
        address_parts = self.extract_address_parts(normalized_address)
        logger.info(f"Части адреса: {address_parts}")

        # Создаем ключ для кэша
        cache_key = f"geocode_{normalized_address}_{city}"

        # Пробуем получить из кэша
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Геокодирование из кэша: {normalized_address}, {city}")
            return cached_result

        # Соблюдаем задержку между запросами
        self._respect_rate_limit()

        try:
            # Формируем варианты запроса (от самого конкретного к самому общему)
            query_variants = []

            # 1. Самый конкретный: улица с номером дома и город
            if city and address_parts['street_only'] and address_parts['house_number']:
                query = f"{address_parts['street_only']}, {city}, Россия"
                query_variants.append(query)

            # 2. Улица с номером дома (без названия улицы, если оно есть) и город
            if city and address_parts['street_without_number'] and address_parts['house_number']:
                # Проверяем, что street_without_number не пустое и не равно street_only
                if (address_parts['street_without_number'] and
                        address_parts['street_without_number'] != address_parts['street_only']):
                    query = f"{address_parts['street_without_number']}, {city}, Россия"
                    query_variants.append(query)

            # 3. Район + улица с номером и город
            if city and address_parts.get('district_street') and address_parts['house_number']:
                query = f"{address_parts['district_street']}, {city}, Россия"
                query_variants.append(query)

            # 4. Район + улица (без номера) и город
            if city and address_parts.get('district') and address_parts['street_without_number']:
                query = f"{address_parts['district']}, {address_parts['street_without_number']}, {city}, Россия"
                query_variants.append(query)

            # 5. Только улица с номером и Россия
            if address_parts['street_only'] and address_parts['house_number']:
                query = f"{address_parts['street_only']}, Россия"
                query_variants.append(query)

            # 6. Полный адрес с городом
            if city and address_parts['full']:
                query = f"{address_parts['full']}, {city}, Россия"
                query_variants.append(query)

            # Убираем дубликаты
            query_variants = list(dict.fromkeys([q for q in query_variants if q and q.strip()]))

            # Если вариантов нет, создаем простой
            if not query_variants and city:
                query_variants.append(f"{city}, Россия")

            logger.info(f"Варианты запроса для '{normalized_address}': {query_variants}")

            if not query_variants:
                logger.warning(f"Не удалось сформировать запросы для адреса: {normalized_address}")
                return self._smart_fallback_geocode(normalized_address, city)

            # Пробуем каждый вариант

                for i, query in enumerate(query_variants):
                    try:
                        # Увеличиваем задержку для OpenStreetMap
                        self._respect_rate_limit()

                        # Дополнительная задержка между запросами
                        if i > 0:
                            time.sleep(1.0)  # 1 секунда между разными вариантами

                        params = {
                            'q': query,
                            'format': 'json',
                            'limit': 1,
                            'addressdetails': 1,
                            'countrycodes': 'ru',
                            'accept-language': 'ru',
                        }

                        logger.info(f"Попытка геокодирования [{i + 1}/{len(query_variants)}]: {query}")

                        # Увеличиваем таймаут
                        response = self.session.get(
                            self.BASE_URL,
                            params=params,
                            timeout=30,  # Увеличиваем таймаут
                            headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (educational-project@rentanalyzer.com)'
                            }
                        )

                        # Проверяем rate limiting
                        if response.status_code == 429:  # Too Many Requests
                            logger.warning("OpenStreetMap rate limit достигнут. Ждем 5 секунд...")
                            time.sleep(5)
                            continue

                        if response.status_code == 403:  # Forbidden
                            logger.error("Доступ запрещен OpenStreetMap. Используем fallback.")
                            break

                        # ... обработка успешного ответа ...

                    except requests.exceptions.Timeout:
                        logger.warning(f"Таймаут для запроса: {query}")
                        continue
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Ошибка сети: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Неожиданная ошибка: {e}")
                        continue

            logger.warning(f"Все варианты не сработали для адреса: {normalized_address}")

        except Exception as e:
            logger.error(f"Общая ошибка геокодирования {address}: {e}")

        # Если не удалось, используем умный fallback
        return self._smart_fallback_geocode(normalized_address, city)

    def _is_just_city(self, result: Dict, city: str = None) -> bool:
        """
        Проверяет, является ли результат просто городом (а не конкретным адресом)
        """
        try:
            address_data = result.get('address', {})
            display_name = result.get('display_name', '').lower()

            # Если в результате есть только город и страна
            if address_data.get('city') and not address_data.get('road') and not address_data.get('street'):
                logger.debug(f"Результат только город: {display_name}")
                return True

            # Если в display_name есть слова, указывающие на город
            city_indicators = ['город', 'city', 'г.', 'населенный пункт']
            for indicator in city_indicators:
                if indicator in display_name and not any(
                        x in display_name for x in ['улица', 'проспект', 'переулок', 'дом']):
                    return True

            # Если результат слишком общий
            if 'россия' in display_name and city and city.lower() in display_name:
                # Считаем количество запятых - если мало, вероятно это город
                if display_name.count(',') < 2:
                    return True

            return False

        except Exception as e:
            logger.error(f"Ошибка проверки 'просто город': {e}")
            return False

    def _is_relevant_result(self, result: Dict, original_address: str, city: str = None) -> bool:
        """
        Проверяет, релевантен ли результат для исходного адреса
        """
        try:
            display_name = result.get('display_name', '').lower()
            address_data = result.get('address', {})

            # Проверяем наличие города в результате
            if city and city.lower() not in display_name:
                # Ищем другие названия города
                city_variants = {
                    'санкт-петербург': ['спб', 'петербург', 'санкт петербург'],
                    'москва': ['мос', 'г. москва'],
                }

                city_lower = city.lower()
                found = False
                if city_lower in city_variants:
                    for variant in city_variants[city_lower]:
                        if variant in display_name:
                            found = True
                            break

                if not found and city_lower not in display_name:
                    logger.debug(f"Город '{city}' не найден в результате: {display_name}")
                    return False

            # Проверяем тип объекта
            osm_type = result.get('osm_type', '')
            # Принимаем узлы, пути и отношения
            if osm_type in ['node', 'way', 'relation']:
                return True

            # Если есть address и там указана улица
            if address_data.get('road') or address_data.get('street'):
                return True

            # Минимальная проверка: результат содержит часть оригинального адреса
            original_lower = original_address.lower()
            for part in original_lower.split():
                if len(part) > 3 and part in display_name:  # Ищем слова длиннее 3 букв
                    return True

            return True  # Принимаем результат по умолчанию

        except Exception as e:
            logger.error(f"Ошибка проверки релевантности: {e}")
            return True  # При ошибке принимаем результат

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
        Резервный метод геокодирования
        """
        try:
            # Координаты основных городов и районов
            district_coordinates = {
                # Санкт-Петербург районы
                'адмиралтейский': {'lat': 59.9170, 'lon': 30.3089},
                'василеостровский': {'lat': 59.9417, 'lon': 30.2579},
                'выборгский': {'lat': 60.0458, 'lon': 30.3392},
                'калининский': {'lat': 60.0057, 'lon': 30.3853},
                'кировский': {'lat': 59.8809, 'lon': 30.2622},
                'колпинский': {'lat': 59.7469, 'lon': 30.5919},
                'красногвардейский': {'lat': 59.9618, 'lon': 30.4763},
                'красносельский': {'lat': 59.8516, 'lon': 30.1397},
                'кронштадтский': {'lat': 59.9904, 'lon': 29.7738},
                'курортный': {'lat': 60.1720, 'lon': 29.8768},
                'московский': {'lat': 59.8511, 'lon': 30.3197},
                'невский': {'lat': 59.8762, 'lon': 30.4627},
                'петроградский': {'lat': 59.9663, 'lon': 30.3115},
                'петродворцовый': {'lat': 59.8801, 'lon': 29.9062},
                'приморский': {'lat': 60.0105, 'lon': 30.2520},
                'пушкинский': {'lat': 59.7194, 'lon': 30.4211},
                'фрунзенский': {'lat': 59.8993, 'lon': 30.3682},
                'центральный': {'lat': 59.9343, 'lon': 30.3611},

                # Москва районы
                'арбат': {'lat': 55.7508, 'lon': 37.5956},
                'тверской': {'lat': 55.7664, 'lon': 37.6035},
                'хамовники': {'lat': 55.7290, 'lon': 37.5636},
                'пресненский': {'lat': 55.7604, 'lon': 37.5595},
            }

            # Пробуем найти район в адресе
            address_lower = address.lower()

            for district, coords in district_coordinates.items():
                if district in address_lower:
                    return {
                        'lat': coords['lat'],
                        'lon': coords['lon'],
                        'display_name': f"{address} (приблизительно, район {district})",
                        'is_approximate': True,
                    }

            # Если район не найден, используем город
            city_coordinates = {
                'москва': {'lat': 55.7558, 'lon': 37.6173},
                'санкт-петербург': {'lat': 59.9343, 'lon': 30.3351},
                'екатеринбург': {'lat': 56.8389, 'lon': 60.6057},
                'новосибирск': {'lat': 55.0084, 'lon': 82.9357},
                'казань': {'lat': 55.8304, 'lon': 49.0661},
                'нижний новгород': {'lat': 56.2965, 'lon': 43.9361},
            }

            if city and city.lower() in city_coordinates:
                coords = city_coordinates[city.lower()]
                return {
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'display_name': f"{address}, {city} (приблизительно)",
                    'is_approximate': True,
                }

            # Если город не найден, используем центр России
            return {
                'lat': 55.7558,
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

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Расчет расстояния между двумя точками (в км)"""
        return calculate_distance(lat1, lon1, lat2, lon2)

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

    def _smart_fallback_geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Умный fallback: генерирует реалистичные координаты в городе
        """
        import random
        import hashlib

        try:
            # В geocoder.py, в методе _smart_fallback_geocode:

            city_info = {
                'санкт-петербург': {
                    'center': {'lat': 59.9343, 'lon': 30.3351},
                    'radius': 0.12,
                    'districts': {
                        'адмиралтейский': {'lat': 59.9170, 'lon': 30.3089, 'radius': 0.02},
                        'василеостровский': {'lat': 59.9417, 'lon': 30.2579, 'radius': 0.02},
                        'выборгский': {'lat': 60.0458, 'lon': 30.3392, 'radius': 0.03},
                        'калининский': {'lat': 60.0057, 'lon': 30.3853, 'radius': 0.03},
                        'кировский': {'lat': 59.8809, 'lon': 30.2622, 'radius': 0.03},
                        'красногвардейский': {'lat': 59.9618, 'lon': 30.4763, 'radius': 0.03},
                        'московский': {'lat': 59.8511, 'lon': 30.3197, 'radius': 0.03},
                        'невский': {'lat': 59.8762, 'lon': 30.4627, 'radius': 0.03},
                        'петроградский': {'lat': 59.9663, 'lon': 30.3115, 'radius': 0.02},
                        'приморский': {'lat': 60.0105, 'lon': 30.2520, 'radius': 0.03},
                        'фрунзенский': {'lat': 59.8993, 'lon': 30.3682, 'radius': 0.03},
                        'центральный': {'lat': 59.9343, 'lon': 30.3611, 'radius': 0.02},
                    }
                },
                'москва': {
                    'center': {'lat': 55.7558, 'lon': 37.6173},
                    'radius': 0.15,
                    'districts': {
                        'арбат': {'lat': 55.7508, 'lon': 37.5956, 'radius': 0.02},
                        'тверской': {'lat': 55.7664, 'lon': 37.6035, 'radius': 0.02},
                        'пресненский': {'lat': 55.7604, 'lon': 37.5595, 'radius': 0.03},
                        'хамовники': {'lat': 55.7290, 'lon': 37.5636, 'radius': 0.03},
                        'замоскворечье': {'lat': 55.7333, 'lon': 37.6333, 'radius': 0.03},
                        'басманный': {'lat': 55.7667, 'lon': 37.6667, 'radius': 0.03},
                    }
                },
                'екатеринбург': {
                    'center': {'lat': 56.8389, 'lon': 60.6057},
                    'radius': 0.08,
                    'districts': {
                        'кировский': {'lat': 56.8500, 'lon': 60.5800, 'radius': 0.02},
                        'ленинский': {'lat': 56.8200, 'lon': 60.5500, 'radius': 0.02},
                        'верх-исетский': {'lat': 56.8400, 'lon': 60.5700, 'radius': 0.02},
                        'орджоникидзевский': {'lat': 56.8800, 'lon': 60.6800, 'radius': 0.03},
                        'железнодорожный': {'lat': 56.8600, 'lon': 60.6100, 'radius': 0.02},
                        'октябрьский': {'lat': 56.8300, 'lon': 60.6500, 'radius': 0.02},
                    }
                },
                'новосибирск': {
                    'center': {'lat': 55.0084, 'lon': 82.9357},
                    'radius': 0.08,
                    'districts': {
                        'дзержинский': {'lat': 55.0500, 'lon': 82.9500, 'radius': 0.02},
                        'калининский': {'lat': 55.0000, 'lon': 82.9800, 'radius': 0.02},
                        'кировский': {'lat': 54.9700, 'lon': 82.9000, 'radius': 0.02},
                        'ленинский': {'lat': 54.9800, 'lon': 82.9200, 'radius': 0.02},
                        'октябрьский': {'lat': 55.0200, 'lon': 82.9600, 'radius': 0.02},
                        'первомайский': {'lat': 54.9500, 'lon': 83.0000, 'radius': 0.02},
                        'советский': {'lat': 54.8500, 'lon': 83.1000, 'radius': 0.02},
                        'центральный': {'lat': 55.0200, 'lon': 82.9200, 'radius': 0.02},
                    }
                },
                'казань': {
                    'center': {'lat': 55.8304, 'lon': 49.0661},
                    'radius': 0.08,
                    'districts': {
                        'вахитовский': {'lat': 55.7900, 'lon': 49.1100, 'radius': 0.02},
                        'кировский': {'lat': 55.8100, 'lon': 49.0900, 'radius': 0.02},
                        'московский': {'lat': 55.8000, 'lon': 49.1300, 'radius': 0.02},
                        'приволжский': {'lat': 55.7800, 'lon': 49.1500, 'radius': 0.02},
                        'советский': {'lat': 55.8000, 'lon': 49.1700, 'radius': 0.02},
                    }
                },
                'нижний новгород': {
                    'center': {'lat': 56.2965, 'lon': 43.9361},
                    'radius': 0.08,
                    'districts': {
                        'автозаводский': {'lat': 56.2500, 'lon': 43.8500, 'radius': 0.02},
                        'канавинский': {'lat': 56.3300, 'lon': 43.9000, 'radius': 0.02},
                        'ленинский': {'lat': 56.2400, 'lon': 44.0000, 'radius': 0.02},
                        'московский': {'lat': 56.3100, 'lon': 43.9500, 'radius': 0.02},
                        'нижегородский': {'lat': 56.2800, 'lon': 44.0300, 'radius': 0.02},
                        'приокский': {'lat': 56.3200, 'lon': 44.0500, 'radius': 0.02},
                        'советский': {'lat': 56.2700, 'lon': 44.0200, 'radius': 0.02},
                        'сормовский': {'lat': 56.3400, 'lon': 43.8700, 'radius': 0.02},
                    }
                },
            }

            if not city:
                return self._simple_fallback_geocode(address, city)

            city_lower = city.lower()

            # Используем хэш адреса для детерминированной "случайности"
            # Это гарантирует, что один и тот же адрес всегда получит одни и те же координаты
            address_hash = hashlib.md5(address.encode()).hexdigest()
            hash_int = int(address_hash[:8], 16)

            # Ищем упоминание района в адресе
            address_lower = address.lower()
            selected_district = None
            district_name = None

            if city_lower in city_info:
                city_data = city_info[city_lower]

                # Ищем район в адресе
                for dist_name, dist_info in city_data['districts'].items():
                    if dist_name in address_lower:
                        selected_district = dist_info
                        district_name = dist_name
                        logger.info(f"Найден район '{district_name}' в адресе")
                        break

                # Генерируем координаты на основе хэша адреса
                if selected_district:
                    # В пределах найденного района
                    # Используем хэш для детерминированного "случайного" смещения
                    lat_offset = ((hash_int % 1000) / 1000.0 - 0.5) * 2 * selected_district['radius']
                    lon_offset = (((hash_int // 1000) % 1000) / 1000.0 - 0.5) * 2 * selected_district['radius']

                    lat = selected_district['lat'] + lat_offset
                    lon = selected_district['lon'] + lon_offset
                    district_desc = district_name
                else:
                    # В пределах всего города
                    lat_offset = ((hash_int % 1000) / 1000.0 - 0.5) * 2 * city_data['radius']
                    lon_offset = (((hash_int // 1000) % 1000) / 1000.0 - 0.5) * 2 * city_data['radius']

                    lat = city_data['center']['lat'] + lat_offset
                    lon = city_data['center']['lon'] + lon_offset
                    district_desc = "случайное место в городе"

                # Ограничиваем координаты
                if selected_district:
                    lat = max(min(lat, selected_district['lat'] + selected_district['radius']),
                              selected_district['lat'] - selected_district['radius'])
                    lon = max(min(lon, selected_district['lon'] + selected_district['radius']),
                              selected_district['lon'] - selected_district['radius'])
                else:
                    lat = max(min(lat, city_data['center']['lat'] + city_data['radius']),
                              city_data['center']['lat'] - city_data['radius'])
                    lon = max(min(lon, city_data['center']['lon'] + city_data['radius']),
                              city_data['center']['lon'] - city_data['radius'])

                result = {
                    'lat': lat,
                    'lon': lon,
                    'display_name': f"{address}, {city} (приблизительно, {district_desc})",
                    'is_approximate': True,
                    'is_fallback': True,
                    'fallback_type': 'smart_random',
                    'address_hash': address_hash[:8],  # для отладки
                }

                logger.info(f"Умный fallback для {address}, {city}: {lat:.6f}, {lon:.6f} (хэш: {address_hash[:8]})")
                return result

            return self._simple_fallback_geocode(address, city)

        except Exception as e:
            logger.error(f"Ошибка умного fallback: {e}")
            return self._simple_fallback_geocode(address, city)

    def extract_address_parts(self, address: str):
        """
        Извлекает части адреса для формирования разных вариантов запроса.
        Улучшенная версия, которая лучше работает с короткими адресами.
        """
        # Убираем лишние пробелы
        cleaned = ' '.join(address.strip().split())
        result = {'full': cleaned}

        # Шаблон для поиска: тип улицы, название, номер дома
        # Пример: "ул. Мира, 66", "проспект Ленина 10Б", "Набережная 90"
        pattern = r'^(?P<street_type>ул\.|улица|пр\.|проспект|наб\.|набережная|б-р|бульвар)?\s*(?P<street_name>[А-Яа-яЁё\s\-]+?)\s*(?P<house_number>\d+[А-Яа-я]?)?$'

        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            street_type = match.group('street_type') or ''
            street_name = match.group('street_name').strip()
            house_number = match.group('house_number')

            # Формируем полное название улицы
            full_street_name = f"{street_type} {street_name}".strip() if street_type else street_name

            # Если есть номер дома, добавляем его
            street_with_number = f"{full_street_name} {house_number}".strip() if house_number else full_street_name

            result.update({
                'street_only': street_with_number,
                'street_without_number': full_street_name,
                'house_number': house_number,
            })
        else:
            # Если не удалось распарсить, используем весь адрес
            result['street_only'] = cleaned
            result['street_without_number'] = cleaned
            result['house_number'] = None

        return result

    def _simple_fallback_geocode(self, address: str, city: str = None) -> Optional[Dict]:
        """
        Простой fallback на случай ошибки в умном
        """
        try:
            city_coordinates = {
                'москва': {'lat': 55.7558, 'lon': 37.6173},
                'санкт-петербург': {'lat': 59.9343, 'lon': 30.3351},
                'екатеринбург': {'lat': 56.8389, 'lon': 60.6057},
                'новосибирск': {'lat': 55.0084, 'lon': 82.9357},
                'казань': {'lat': 55.8304, 'lon': 49.0661},
                'нижний новгород': {'lat': 56.2965, 'lon': 43.9361},
            }

            if city and city.lower() in city_coordinates:
                coords = city_coordinates[city.lower()]
                return {
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'display_name': f"{address}, {city} (приблизительно, центр города)",
                    'is_approximate': True,
                    'is_fallback': True,
                    'fallback_type': 'city_center',
                }

            # Центр России
            return {
                'lat': 55.7558,
                'lon': 37.6173,
                'display_name': f"{address}, {city} (приблизительно, центр России)",
                'is_approximate': True,
                'is_fallback': True,
                'fallback_type': 'russia_center',
            }

        except Exception as e:
            logger.error(f"Ошибка простого fallback: {e}")
            return None


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Расчет расстояния между двумя точками на Земле (в километрах)
    по формуле гаверсинусов
    """
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

# Создаем глобальный экземпляр
geocoder = OpenStreetMapGeocoder()