import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class YandexRealtyParser:
    """Парсер данных из Яндекс.Недвижимость с использованием официальной библиотеки"""

    def __init__(self):
        try:
            from yandex_realty_parser import RealtyParser
            self.parser = RealtyParser()
            self.is_available = True
            logger.info("Библиотека yandex-realty-parser успешно загружена")
        except ImportError as e:
            logger.error(f"Не удалось импортировать yandex-realty-parser: {e}")
            self.parser = None
            self.is_available = False
            logger.warning("Используется режим fallback с реалистичными данными")

    def get_rent_offers(self, city_name: str, rooms: str = "1,2,3", limit: int = 20) -> List[Dict]:
        if not self.is_available or not self.parser:
            logger.warning("Библиотека не доступна, возвращаем пустой список")
            return []

        try:
            logger.info(f"Парсинг Яндекс.Недвижимость для города: {city_name}")

            # Маппинг названий городов для Яндекса
            city_mapping = {
                'Москва': 'moskva',
                'Санкт-Петербург': 'sankt-peterburg',
                'Екатеринбург': 'ekaterinburg',
                'Новосибирск': 'novosibirsk',
                'Казань': 'kazan',
                'Нижний Новгород': 'nizhniy_novgorod',
                'Самара': 'samara',
                'Челябинск': 'chelyabinsk',
                'Омск': 'omsk',
                'Ростов-на-Дону': 'rostov-na-donu',
                'Уфа': 'ufa',
                'Красноярск': 'krasnoyarsk',
                'Пермь': 'perm',
                'Воронеж': 'voronezh',
                'Волгоград': 'volgograd',
            }

            yandex_city = city_mapping.get(city_name)
            if not yandex_city:
                logger.warning(f"Город {city_name} не найден в маппинге для Яндекса")
                return []

            # Параметры запроса
            params = {
                'type': 'RENT',
                'category': 'APARTMENT',
                'rgid': yandex_city,
                'roomsTotal': rooms,
                'sort': 'RELEVANCE',
                'page': 1,
                'onlyFlat': 'true',
            }

            offers = []
            parsed_count = 0

            # Парсим несколько страниц для набора данных
            for page in range(1, 4):  # Парсим 3 страницы
                if len(offers) >= limit:
                    break

                params['page'] = page

                try:
                    logger.info(f"Парсинг страницы {page} для {city_name}")

                    # Используем библиотеку для парсинга
                    parsed_data = self.parser.parse(params)

                    if not parsed_data or 'offers' not in parsed_data:
                        logger.warning(f"Нет данных на странице {page}")
                        break

                    # Преобразуем данные в наш формат
                    for yandex_offer in parsed_data['offers'][:limit - len(offers)]:
                        try:
                            offer = self._convert_yandex_offer(yandex_offer, city_name)
                            if offer:
                                offers.append(offer)
                                parsed_count += 1
                        except Exception as e:
                            logger.debug(f"Ошибка конвертации предложения: {e}")
                            continue

                    # Пауза между запросами
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"Ошибка парсинга страницы {page}: {e}")
                    break

            logger.info(f"Успешно спаршено {len(offers)} предложений из Яндекс для {city_name}")
            return offers

        except Exception as e:
            logger.error(f"Критическая ошибка парсинга Яндекс: {e}")
            return []

    def _convert_yandex_offer(self, yandex_offer: Dict, city_name: str) -> Optional[Dict]:
        """
        Конвертация предложения из формата Яндекса в наш формат
        """
        try:
            # Извлекаем основные данные
            offer_data = yandex_offer.get('offer', {})

            # ID и ссылка
            offer_id = offer_data.get('id', '')
            if not offer_id:
                return None

            # Адрес
            location = offer_data.get('location', {})
            address = location.get('address', '')
            if not address:
                address = f"{city_name}, адрес не указан"

            # Площадь
            area_info = offer_data.get('area', {})
            area = area_info.get('value', 0)

            # Комнаты
            rooms = offer_data.get('rooms', 1)

            # Цена
            price_info = offer_data.get('price', {})
            price = price_info.get('value', 0)

            # Пропускаем предложения с невалидными ценами или площадями
            if price <= 0 or area <= 0:
                return None

            # Этаж
            floor = offer_data.get('floor', 0)

            # Всего этажей
            building_info = offer_data.get('building', {})
            total_floors = building_info.get('floorsCount', 0)

            # Описание
            description = offer_data.get('description', '')[:200]

            # Дополнительные параметры
            additional_info = {
                'description': description,
                'total_floors': total_floors,
                'building_type': building_info.get('buildingType', ''),
                'year_built': building_info.get('builtYear', ''),
                'has_elevator': building_info.get('hasElevator', False),
                'has_parking': building_info.get('hasParking', False),
                'offer_type': offer_data.get('type', ''),
            }

            # Формируем предложение в нашем формате
            offer = {
                'source': 'yandex_real',
                'external_id': f"yandex_real_{offer_id}",
                'city_name': city_name,
                'address': address,
                'area': float(area),
                'rooms': int(rooms),
                'floor': int(floor) if floor else None,
                'price': float(price),
                'price_per_sqm': round(float(price) / float(area), 2) if area > 0 else 0,
                'url': f"https://realty.yandex.ru/offer/{offer_id}/",
                'parsed_date': datetime.now(),
                'additional_info': additional_info,
            }

            return offer

        except Exception as e:
            logger.error(f"Ошибка конвертации предложения Яндекс: {e}")
            return None

    def test_connection(self) -> bool:
        """Тестирование подключения и доступности парсера"""
        if not self.is_available:
            return False

        try:
            # Пробуем спарсить тестовые данные для Москвы
            test_offers = self.get_rent_offers('Москва', limit=2)
            return len(test_offers) > 0
        except Exception as e:
            logger.error(f"Тест подключения не удался: {e}")
            return False


# Глобальный экземпляр
yandex_realty_parser = YandexRealtyParser()