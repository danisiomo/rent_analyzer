"""
Модуль для получения данных из Avito (публичный доступ)
"""
import requests
import re
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class AvitoParser:
    """Парсер публичных данных Avito (для образовательных целей)"""

    BASE_URL = "https://www.avito.ru"

    # Города и их коды в Avito
    CITIES = {
        'Москва': 'moskva',
        'Санкт-Петербург': 'sankt-peterburg',
        'Екатеринбург': 'ekaterinburg',
        'Новосибирск': 'novosibirsk',
        'Казань': 'kazan',
        'Нижний Новгород': 'nizhniy_novgorod',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })

    def get_rent_offers(self, city_name: str, rooms: int = None, limit: int = 10) -> List[Dict]:
        """
        Получение предложений об аренде из Avito

        Внимание: Для образовательных целей! Уважайте robots.txt и ограничения!
        """
        city_code = self.CITIES.get(city_name)
        if not city_code:
            return []

        offers = []

        try:
            # Формируем URL для поиска
            url = f"{self.BASE_URL}/{city_code}/kvartiry/sdam/na_dlitelnyy_srok"

            if rooms:
                url += f"-{rooms}_komnaty"

            logger.info(f"Запрос Avito: {url}")

            # Делаем запрос
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                offers = self._parse_avito_page(response.text, city_name, limit)
            else:
                logger.warning(f"Avito вернул статус {response.status_code}")

            # Пауза между запросами
            time.sleep(2)

        except Exception as e:
            logger.error(f"Ошибка при запросе Avito: {e}")

        return offers

    def _parse_avito_page(self, html: str, city_name: str, limit: int) -> List[Dict]:
        """Парсинг HTML страницы Avito"""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        try:
            # Находим все карточки объявлений
            items = soup.find_all('div', {'data-marker': 'item'})

            for item in items[:limit]:
                try:
                    # Извлекаем данные
                    title_elem = item.find('h3', {'itemprop': 'name'})
                    title = title_elem.text.strip() if title_elem else ''

                    # Адрес
                    address_elem = item.find('div', {'class': re.compile('geo-georeferences')})
                    address = address_elem.text.strip() if address_elem else ''

                    # Цена
                    price_elem = item.find('meta', {'itemprop': 'price'})
                    price = float(price_elem['content']) if price_elem and 'content' in price_elem.attrs else 0

                    # Площадь и комнаты из заголовка
                    area = 0
                    rooms = 1

                    # Пытаемся извлечь из заголовка
                    title_lower = title.lower()
                    if 'м²' in title:
                        area_match = re.search(r'(\d+[,.]?\d*)\s*м²', title)
                        if area_match:
                            area = float(area_match.group(1).replace(',', '.'))

                    # Комнаты
                    if '1-к' in title_lower or '1 комн' in title_lower:
                        rooms = 1
                    elif '2-к' in title_lower or '2 комн' in title_lower:
                        rooms = 2
                    elif '3-к' in title_lower or '3 комн' in title_lower:
                        rooms = 3
                    elif '4-к' in title_lower or '4 комн' in title_lower:
                        rooms = 4

                    # Ссылка
                    link_elem = item.find('a', {'data-marker': 'item-title'})
                    relative_url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''
                    url = f"{self.BASE_URL}{relative_url}" if relative_url else ''

                    # ID объявления
                    item_id = item.get('data-item-id', '')

                    if price > 1000 and area > 10:  # Фильтр валидных данных
                        offer = {
                            'source': 'avito',
                            'external_id': f"avito_{item_id}",
                            'city_name': city_name,
                            'address': f"{address}, {title}",
                            'area': area,
                            'rooms': rooms,
                            'price': price,
                            'url': url,
                            'parsed_date': time.time(),
                        }
                        offers.append(offer)

                except Exception as e:
                    logger.debug(f"Ошибка парсинга карточки Avito: {e}")
                    continue

        except Exception as e:
            logger.error(f"Ошибка парсинга страницы Avito: {e}")

        logger.info(f"Найдено {len(offers)} предложений в Avito для {city_name}")
        return offers


# Глобальный экземпляр
avito_parser = AvitoParser()