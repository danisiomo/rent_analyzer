
import pandas as pd
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.db.models import Q
from analyzer.models import Apartment, MarketOffer
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import math


def calculate_distance(lat1, lon1, lat2, lon2):
    """Расчет расстояния между двумя точками в километрах"""
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')

    # Конвертируем градусы в радианы
    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    # Радиус Земли в км
    R = 6371.0

    # Разницы координат
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Формула гаверсинусов
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


class ApartmentAnalyzer:
    """Исправленный класс для анализа квартир с учетом расстояния"""

    def __init__(self, apartment: Apartment):
        self.apartment = apartment
        self.city = apartment.city
        self.similar_offers = []
        self.analysis_results = {}

    def find_similar_offers(
            self,
            area_tolerance: float = 20.0,
            price_tolerance: float = 30.0,
            include_same_floor: bool = False,
            max_distance_km: float = 10.0,
            max_results: int = 50
    ) -> List[MarketOffer]:
        """
        Поиск похожих предложений с учетом расстояния

        Args:
            area_tolerance: Допустимое отклонение по площади в %
            price_tolerance: Допустимое отклонение по цене в %
            include_same_floor: Учитывать только тот же этаж
            max_distance_km: Максимальное расстояние в км
            max_results: Максимальное количество результатов
        """
        import logging
        logger = logging.getLogger(__name__)

        # Базовые параметры квартиры
        apartment_area = float(self.apartment.area)
        desired_price = float(self.apartment.desired_price) if self.apartment.desired_price else None
        apartment_lat = float(self.apartment.latitude) if self.apartment.latitude else None
        apartment_lon = float(self.apartment.longitude) if self.apartment.longitude else None

        logger.info(f"Поиск похожих предложений для: {self.apartment.address}")
        logger.info(
            f"Параметры: площадь ±{area_tolerance}%, цена ±{price_tolerance}%, расстояние до {max_distance_km}км")

        # Базовые фильтры по городу и активности
        filters = Q(city=self.city) & Q(is_active=True)

        # Фильтр по количеству комнат (с небольшим допуском)
        filters &= Q(rooms=self.apartment.rooms)

        # Фильтр по площади
        area_min = apartment_area * (1 - area_tolerance / 100)
        area_max = apartment_area * (1 + area_tolerance / 100)
        filters &= Q(area__gte=area_min) & Q(area__lte=area_max)

        # Фильтр по цене (если есть желаемая цена)
        if desired_price:
            price_min = desired_price * (1 - price_tolerance / 100)
            price_max = desired_price * (1 + price_tolerance / 100)
            filters &= Q(price__gte=price_min) & Q(price__lte=price_max)

        # Фильтр по этажу (опционально)
        if include_same_floor and self.apartment.floor:
            filters &= Q(floor=self.apartment.floor)

        # Получаем все предложения по фильтрам
        all_offers = MarketOffer.objects.filter(filters).order_by('price')

        logger.info(f"Найдено предложений по базовым фильтрам: {all_offers.count()}")

        # Фильтрация по расстоянию
        filtered_offers = []

        if apartment_lat and apartment_lon and max_distance_km > 0:
            # Есть координаты квартиры, фильтруем по расстоянию
            for offer in all_offers:
                if offer.latitude and offer.longitude:
                    distance = calculate_distance(
                        apartment_lat, apartment_lon,
                        float(offer.latitude), float(offer.longitude)
                    )
                    offer.distance_km = distance

                    if distance <= max_distance_km:
                        filtered_offers.append(offer)
                    else:
                        logger.debug(f"Предложение {offer.id} слишком далеко: {distance:.1f} км")
                else:
                    # У предложения нет координат, все равно добавляем
                    offer.distance_km = None
                    filtered_offers.append(offer)
        else:
            # Нет координатов или не указано ограничение по расстоянию
            filtered_offers = list(all_offers)
            for offer in filtered_offers:
                offer.distance_km = None

        # Сортируем по расстоянию (если есть)
        try:
            filtered_offers.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))
        except:
            pass

        # Ограничиваем количество результатов
        self.similar_offers = filtered_offers[:max_results]

        # Статистика по расстоянию
        distances = [o.distance_km for o in self.similar_offers if o.distance_km is not None]
        if distances:
            avg_distance = sum(distances) / len(distances)
            logger.info(f"Среднее расстояние похожих предложений: {avg_distance:.1f} км")

        logger.info(f"Итоговое количество похожих предложений: {len(self.similar_offers)}")

        return self.similar_offers

    def calculate_statistics(self) -> Dict:
        """Расчет статистики по похожим предложениям"""
        if not self.similar_offers:
            return {
                'count': 0,
                'avg_price': Decimal('0'),
                'median_price': Decimal('0'),
                'min_price': Decimal('0'),
                'max_price': Decimal('0'),
                'avg_price_per_sqm': Decimal('0'),
                'price_range': '0 - 0',
            }

        # Собираем данные
        prices = [float(offer.price) for offer in self.similar_offers]
        areas = [float(offer.area) for offer in self.similar_offers]

        # Рассчитываем статистику
        avg_price = sum(prices) / len(prices)
        median_price = np.median(prices)
        min_price = min(prices)
        max_price = max(prices)

        # Цена за м²
        prices_per_sqm = []
        for price, area in zip(prices, areas):
            if area > 0:
                prices_per_sqm.append(price / area)

        avg_price_per_sqm = sum(prices_per_sqm) / len(prices_per_sqm) if prices_per_sqm else 0

        # Формируем результаты
        self.analysis_results = {
            'count': len(self.similar_offers),
            'avg_price': Decimal(str(round(avg_price, 2))),
            'median_price': Decimal(str(round(median_price, 2))),
            'min_price': Decimal(str(round(min_price, 2))),
            'max_price': Decimal(str(round(max_price, 2))),
            'avg_price_per_sqm': Decimal(str(round(avg_price_per_sqm, 2))),
            'price_range': f"{min_price:,.0f} - {max_price:,.0f}",
        }

        return self.analysis_results

    def generate_recommendation(self) -> Dict:
        """Генерация рекомендации на основе анализа"""
        if not self.analysis_results or self.analysis_results['count'] == 0:
            return {
                'fair_price': self.apartment.desired_price or Decimal('0'),
                'price_difference_percent': Decimal('0'),
                'price_difference_rub': Decimal('0'),
                'recommendation': 'Недостаточно данных для анализа. Попробуйте увеличить допустимые отклонения или радиус поиска.',
                'recommendation_type': 'info',
                'confidence': 'low',
            }

        # Используем медианную цену как справедливую
        fair_price = self.analysis_results['median_price']
        desired_price = self.apartment.desired_price or fair_price

        # Преобразуем в float для расчетов
        fair_price_float = float(fair_price)
        desired_price_float = float(desired_price)

        # Разница в рублях
        price_difference_rub = desired_price_float - fair_price_float

        # Разница в процентах (от справедливой цены)
        if fair_price_float > 0:
            price_difference_percent = (price_difference_rub / fair_price_float) * 100
        else:
            price_difference_percent = 0

        # Определяем тип рекомендации
        if self.analysis_results['count'] < 3:
            recommendation = "Мало данных для точного анализа"
            recommendation_type = "warning"
            confidence = "low"

        elif abs(price_difference_percent) <= 5:
            recommendation = "✅ Ваша цена оптимальна и близка к рыночной"
            recommendation_type = "success"
            confidence = "high"

        elif price_difference_percent > 5:  # Желаемая цена ВЫШЕ справедливой
            recommendation = f"⚠️ Ваша цена завышена на {abs(price_difference_percent):.1f}%"
            recommendation_type = "warning"
            confidence = "medium"

        else:  # price_difference_percent < -5 (желаемая цена НИЖЕ справедливой)
            recommendation = f"💰 Ваша цена занижена на {abs(price_difference_percent):.1f}%"
            recommendation_type = "info"
            confidence = "medium"

        # Добавляем детали
        recommendation += f". Рыночный диапазон: {self.analysis_results['price_range']} руб."

        # Добавляем совет
        if price_difference_percent < -10:  # Сильно занижена
            recommendation += f"\n💡 Совет: Можете повысить цену до {fair_price_float:,.0f} руб. для получения большей прибыли."
        elif price_difference_percent > 10:  # Сильно завышена
            recommendation += f"\n💡 Совет: Рекомендуем снизить цену до {fair_price_float:,.0f} руб. для быстрой сдачи."

        # Если данных мало, добавляем рекомендацию
        if self.analysis_results['count'] < 5:
            recommendation += f"\n📊 Для более точного анализа добавьте больше фильтров или увеличьте радиус поиска."

        return {
            'fair_price': fair_price_float,
            'price_difference_percent': price_difference_percent,
            'price_difference_rub': price_difference_rub,
            'recommendation': recommendation,
            'recommendation_type': recommendation_type,
            'confidence': confidence,
            'suggested_price': fair_price_float,
        }

    def analyze(self, **kwargs) -> Dict:
        """Полный анализ квартиры"""
        # Ищем похожие предложения
        self.find_similar_offers(**kwargs)

        # Рассчитываем статистику
        statistics = self.calculate_statistics()

        # Генерируем рекомендацию
        recommendation = self.generate_recommendation()

        # Объединяем результаты
        results = {
            **statistics,
            **recommendation,
            'apartment': self.apartment,
        }

        return results