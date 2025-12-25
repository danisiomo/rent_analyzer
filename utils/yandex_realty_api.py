"""
Модуль для получения реальных данных из Яндекс.Недвижимость
"""
import requests
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class YandexRealtyAPI:
    """API для получения данных о недвижимости из Яндекс"""

    BASE_URL = "https://realty.yandex.ru/gate/react-page/get"

    # ID регионов для поиска
    REGION_IDS = {
        'Москва': 1,
        'Санкт-Петербург': 2,
        'Екатеринбург': 3,
        'Новосибирск': 65,
        'Казань': 43,
        'Нижний Новгород': 47,
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://realty.yandex.ru/',
        })

    def get_rent_offers(self, city_name: str, rooms: str = "1,2,3", limit: int = 20) -> List[Dict]:
        """
        Получение предложений об аренде из Яндекс.Недвижимость

        Args:
            city_name: Название города
            rooms: Тип квартиры (1,2,3)
            limit: Максимальное количество предложений

        Returns:
            Список предложений
        """
        region_id = self.REGION_IDS.get(city_name)
        if not region_id:
            logger.warning(f"Город {city_name} не найден в Яндекс.Недвижимость")
            return []

        try:
            # Параметры запроса
            params = {
                'page': 'SEARCH',
                'type': 'RENT',
                'category': 'APARTMENT',
                'rgid': region_id,
                'roomsTotal': rooms,
                '_pageType': 'search',
                'sort': 'RELEVANCE',
                'showGeo': 'NO',
            }

            logger.info(f"Запрос Яндекс.Недвижимость для {city_name} (rgid: {region_id})")

            response = self.session.get(self.BASE_URL, params=params, timeout=15)

            if response.status_code == 200:
                return self._parse_yandex_response(response.json(), city_name, limit)
            else:
                logger.error(f"Ошибка Яндекс API: {response.status_code}")

        except Exception as e:
            logger.error(f"Ошибка при запросе Яндекс: {e}")

        return []

    def _parse_yandex_response(self, data: dict, city_name: str, limit: int) -> List[Dict]:
        """Парсинг ответа от Яндекс.Недвижимость"""
        offers = []

        try:
            # Извлекаем данные из сложной структуры ответа
            search_data = data.get('response', {}).get('search', {})
            offers_data = search_data.get('offers', [])

            for offer_data in offers_data[:limit]:
                try:
                    # Основные параметры
                    main_info = offer_data.get('offer', {})

                    # Адрес
                    location = main_info.get('location', {})
                    address = location.get('address', '')

                    # Площадь
                    area = main_info.get('area', {}).get('value', 0)

                    # Комнаты
                    rooms = main_info.get('rooms', 1)

                    # Цена
                    price_info = main_info.get('price', {})
                    price = price_info.get('value', 0)

                    # Этаж
                    floor = main_info.get('floor', 0)
                    total_floors = main_info.get('building', {}).get('floorsCount', 0)

                    # Ссылка
                    offer_id = main_info.get('id', '')
                    url = f"https://realty.yandex.ru/offer/{offer_id}/" if offer_id else ''

                    # Дополнительная информация
                    description = main_info.get('description', '')[:200]

                    if price > 0 and area > 0:  # Только валидные предложения
                        offer = {
                            'source': 'yandex',
                            'external_id': f"yandex_{offer_id}",
                            'city_name': city_name,
                            'address': address,
                            'area': float(area),
                            'rooms': int(rooms),
                            'floor': int(floor) if floor else None,
                            'total_floors': int(total_floors) if total_floors else None,
                            'price': float(price),
                            'url': url,
                            'description': description,
                            'parsed_date': datetime.now().isoformat(),
                        }
                        offers.append(offer)

                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Ошибка парсинга предложения Яндекс: {e}")
                    continue

        except Exception as e:
            logger.error(f"Ошибка парсинга ответа Яндекс: {e}")

        logger.info(f"Найдено {len(offers)} предложений в Яндекс для {city_name}")
        return offers


# Глобальный экземпляр
yandex_api = YandexRealtyAPI()