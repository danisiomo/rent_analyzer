import pandas as pd
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.db.models import Q, Avg, Min, Max, Count
from analyzer.models import Apartment, MarketOffer, City
import numpy as np
from decimal import Decimal, ROUND_HALF_UP

def decimal_to_float(value):
    """Безопасное преобразование Decimal в float"""
    if isinstance(value, Decimal):
        return float(value)
    return float(value)

def decimal_to_json(value):
    """Конвертирует Decimal в JSON-совместимый формат"""
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, dict):
        return {k: decimal_to_json(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [decimal_to_json(v) for v in value]
    else:
        return value

def float_to_decimal(value, precision=2):
    """Безопасное преобразование float в Decimal"""
    if isinstance(value, float):
        return Decimal(str(round(value, precision)))
    elif isinstance(value, Decimal):
        return value.quantize(Decimal(f'1.{precision}'), rounding=ROUND_HALF_UP)
    return Decimal(str(value))

class ApartmentAnalyzer:
    """Класс для анализа квартир и поиска похожих предложений"""

    def __init__(self, apartment: Apartment):
        self.apartment = apartment
        self.city = apartment.city
        self.similar_offers = []
        self.analysis_results = {}

    def find_similar_offers(
            self,
            area_tolerance: float = 20.0,  # Проценты
            price_tolerance: float = 30.0,  # Проценты
            include_same_floor: bool = False,  # По умолчанию не включаем тот же этаж
            max_distance_km: float = 10.0,  # Максимальное расстояние в км
            max_results: int = 50
    ) -> List[MarketOffer]:
        """
        Поиск похожих рыночных предложений с учетом всех фильтров
        """
        import logging
        logger = logging.getLogger(__name__)

        # Преобразуем Decimal в float для расчетов
        apartment_area = float(self.apartment.area)
        desired_price = float(self.apartment.desired_price) if self.apartment.desired_price else None

        # Координаты квартиры
        apartment_lat = float(self.apartment.latitude) if self.apartment.latitude else None
        apartment_lon = float(self.apartment.longitude) if self.apartment.longitude else None

        logger.info(f"Поиск похожих предложений для квартиры:")
        logger.info(f"  Город: {self.apartment.city.name}")
        logger.info(f"  Комнат: {self.apartment.rooms}")
        logger.info(f"  Площадь: {apartment_area} м²")
        logger.info(f"  Допуск по площади: ±{area_tolerance}%")
        logger.info(f"  Допуск по цене: ±{price_tolerance}%")
        logger.info(f"  Макс. расстояние: {max_distance_km} км")

        # Базовые фильтры: город, активные, примерно столько же комнат
        # Расширяем фильтр по комнатам: ищем +/- 1 комнату
        rooms_filter = Q(rooms=self.apartment.rooms)
        if self.apartment.rooms > 1:
            rooms_filter = rooms_filter | Q(rooms=self.apartment.rooms - 1)
        rooms_filter = rooms_filter | Q(rooms=self.apartment.rooms + 1)

        filters = Q(city=self.apartment.city) & Q(is_active=True) & rooms_filter

        logger.info(f"Базовый фильтр: {MarketOffer.objects.filter(filters).count()} предложений")

        # Фильтр по площади (в абсолютных значениях, а не процентах)
        # area_tolerance - это проценты, преобразуем в абсолютное значение
        area_tolerance_value = apartment_area * (area_tolerance / 100.0)
        area_min = apartment_area - area_tolerance_value
        area_max = apartment_area + area_tolerance_value

        filters &= Q(area__gte=area_min) & Q(area__lte=area_max)
        logger.info(
            f"После фильтра по площади ({area_min:.1f}-{area_max:.1f} м²): {MarketOffer.objects.filter(filters).count()}")

        # Фильтр по цене (если указана желаемая цена)
        if desired_price:
            price_tolerance_value = desired_price * (price_tolerance / 100.0)
            price_min = desired_price - price_tolerance_value
            price_max = desired_price + price_tolerance_value

            filters &= Q(price__gte=price_min) & Q(price__lte=price_max)
            logger.info(
                f"После фильтра по цене ({price_min:,.0f}-{price_max:,.0f} руб.): {MarketOffer.objects.filter(filters).count()}")

        # Фильтр по этажу (опционально)
        if include_same_floor and self.apartment.floor:
            filters &= Q(floor=self.apartment.floor)
            logger.info(
                f"После фильтра по этажу ({self.apartment.floor}): {MarketOffer.objects.filter(filters).count()}")

        # Получаем ВСЕ предложения по фильтрам
        all_offers = MarketOffer.objects.filter(filters)
        logger.info(f"Всего после базовых фильтров: {all_offers.count()}")

        # Фильтрация по расстоянию (если есть координаты квартиры и указано ограничение)
        filtered_offers = []

        if apartment_lat and apartment_lon and max_distance_km > 0:
            from utils.distance_calculator import calculate_distance

            for offer in all_offers:
                # Проверяем, есть ли у предложения координаты
                if offer.latitude and offer.longitude:
                    try:
                        # Рассчитываем расстояние
                        distance = calculate_distance(
                            apartment_lat, apartment_lon,
                            float(offer.latitude), float(offer.longitude)
                        )

                        # Сохраняем расстояние как дополнительное поле
                        offer.distance_km = round(distance, 1)

                        # Проверяем, попадает ли в радиус
                        if distance <= max_distance_km:
                            filtered_offers.append(offer)
                        else:
                            logger.debug(f"Предложение {offer.id} слишком далеко: {distance:.1f} км")
                    except Exception as e:
                        logger.error(f"Ошибка расчета расстояния для предложения {offer.id}: {e}")
                        # Если ошибка, все равно добавляем
                        filtered_offers.append(offer)
                else:
                    # Если у предложения нет координатов, добавляем с расстоянием "неизвестно"
                    offer.distance_km = None
                    filtered_offers.append(offer)
                    logger.debug(f"У предложения {offer.id} нет координатов")
        else:
            # Если нет координат квартиры или не указано ограничение по расстоянию
            filtered_offers = list(all_offers)
            logger.info("Фильтрация по расстоянию отключена")

        # Сортируем по расстоянию (если оно есть), затем по цене
        try:
            filtered_offers.sort(key=lambda x: (
                getattr(x, 'distance_km', float('inf')),  # Сначала по расстоянию
                float(x.price)  # Затем по цене
            ))
        except:
            # Если сортировка не удалась, сортируем просто по цене
            filtered_offers.sort(key=lambda x: float(x.price))

        # Ограничиваем количество результатов
        self.similar_offers = filtered_offers[:max_results]

        # Логируем статистику
        if apartment_lat and apartment_lon:
            distances = [getattr(o, 'distance_km', None) for o in self.similar_offers if
                         hasattr(o, 'distance_km') and o.distance_km is not None]
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

        # Собираем данные (преобразуем Decimal в float для расчетов)
        prices = [float(offer.price) for offer in self.similar_offers]
        areas = [float(offer.area) for offer in self.similar_offers]

        # Рассчитываем статистику
        avg_price = sum(prices) / len(prices)
        median_price = np.median(prices)
        min_price = min(prices)
        max_price = max(prices)

        # Цена за м²
        prices_per_sqm = [price / area for price, area in zip(prices, areas) if area > 0]
        avg_price_per_sqm = sum(prices_per_sqm) / len(prices_per_sqm) if prices_per_sqm else 0

        # Формируем результаты (возвращаем как Decimal)
        self.analysis_results = {
            'count': len(self.similar_offers),
            'avg_price': Decimal(str(avg_price)),
            'median_price': Decimal(str(median_price)),
            'min_price': Decimal(str(min_price)),
            'max_price': Decimal(str(max_price)),
            'avg_price_per_sqm': Decimal(str(avg_price_per_sqm)),
            'price_range': f"{min_price:.0f} - {max_price:.0f}",
            'similar_offers': self.similar_offers,
        }

        return self.analysis_results

    def generate_recommendation(self) -> Dict:
        """Генерация рекомендации на основе анализа"""
        if not self.analysis_results or self.analysis_results['count'] == 0:
            return {
                'fair_price': self.apartment.desired_price or Decimal('0'),
                'price_difference': Decimal('0'),
                'recommendation': 'Недостаточно данных для анализа',
                'recommendation_type': 'info',
                'confidence': 'low',
            }

        # Используем медианную цену как справедливую
        fair_price = self.analysis_results['median_price']
        desired_price = self.apartment.desired_price or fair_price

        # Преобразуем в float для расчетов
        fair_price_float = float(fair_price)
        desired_price_float = float(desired_price)

        # РАСЧЕТ РАЗНИЦЫ: нужно определить ПРОЦЕНТ ОТКЛОНЕНИЯ желаемой цены от справедливой
        if desired_price_float > 0:
            # Процент, на который желаемая цена отличается от справедливой
            # Если желаемая цена меньше справедливой, разница будет отрицательной
            price_difference_percent = ((desired_price_float - fair_price_float) / fair_price_float) * 100
        else:
            price_difference_percent = 0

        # Абсолютная разница в рублях
        price_difference_rub = desired_price_float - fair_price_float

        # Определяем тип рекомендации
        if abs(price_difference_percent) <= 5:
            recommendation = "Ваша цена близка к рыночной"
            recommendation_type = "success"
            confidence = "high"
        elif price_difference_percent > 0:  # Желаемая цена ВЫШЕ справедливой
            recommendation = f"Ваша цена завышена на {abs(price_difference_percent):.1f}%"
            recommendation_type = "danger"
            confidence = "medium"
        else:  # Желаемая цена НИЖЕ справедливой (price_difference_percent < 0)
            recommendation = f"Ваша цена занижена на {abs(price_difference_percent):.1f}%"
            recommendation_type = "warning"
            confidence = "medium"

        # Добавляем детали
        recommendation += f". Рыночный диапазон: {self.analysis_results['price_range']} руб."

        # Добавляем совет
        if price_difference_percent < -5:  # Сильно занижена
            recommendation += f"\nСовет: Рассмотрите возможность повышения цены до {fair_price_float:,.0f} руб."
        elif price_difference_percent > 5:  # Сильно завышена
            recommendation += f"\nСовет: Рассмотрите возможность снижения цены до {fair_price_float:,.0f} руб."

        return {
            'fair_price': float(fair_price),
            'price_difference': float(price_difference_percent),  # Процент разницы
            'price_difference_rub': float(price_difference_rub),  # Разница в рублях
            'recommendation': recommendation,
            'recommendation_type': recommendation_type,
            'confidence': confidence,
            'suggested_price': float(fair_price),
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

        # Убираем список предложений из основного вывода (слишком большой)
        if 'similar_offers' in results:
            del results['similar_offers']

        return results