from django.core.management.base import BaseCommand
from analyzer.models import Apartment, MarketOffer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирование фильтров поиска похожих предложений'

    def add_arguments(self, parser):
        parser.add_argument('--apartment_id', type=int, required=True, help='ID квартиры')

    def handle(self, *args, **options):
        apartment_id = options['apartment_id']
        apartment = Apartment.objects.get(id=apartment_id)

        self.stdout.write(f"Тестирование фильтров для квартиры:")
        self.stdout.write(f"  Адрес: {apartment.address}")
        self.stdout.write(f"  Город: {apartment.city.name}")
        self.stdout.write(f"  Комнат: {apartment.rooms}")
        self.stdout.write(f"  Площадь: {apartment.area} м²")
        self.stdout.write(f"  Цена: {apartment.desired_price} руб.")
        self.stdout.write("=" * 60)

        # Все активные предложения в городе
        total_in_city = MarketOffer.objects.filter(city=apartment.city, is_active=True).count()
        self.stdout.write(f"Всего активных предложений в {apartment.city.name}: {total_in_city}")

        # По комнатам в городе
        by_rooms = MarketOffer.objects.filter(
            city=apartment.city,
            rooms=apartment.rooms,
            is_active=True
        ).count()
        self.stdout.write(f"Предложений {apartment.rooms}-к в {apartment.city.name}: {by_rooms}")

        # Тестируем разные допуски
        self.stdout.write("\nТестирование разных допусков:")

        area_tolerances = [5, 10, 15, 20, 30]
        price_tolerances = [10, 15, 20, 30, 50]

        apartment_area = float(apartment.area)
        desired_price = float(apartment.desired_price)

        for area_tol in area_tolerances:
            for price_tol in price_tolerances:
                area_min = apartment_area * (1 - area_tol / 100)
                area_max = apartment_area * (1 + area_tol / 100)
                price_min = desired_price * (1 - price_tol / 100)
                price_max = desired_price * (1 + price_tol / 100)

                count = MarketOffer.objects.filter(
                    city=apartment.city,
                    rooms=apartment.rooms,
                    is_active=True,
                    area__gte=area_min,
                    area__lte=area_max,
                    price__gte=price_min,
                    price__lte=price_max
                ).count()

                self.stdout.write(f"  Площадь ±{area_tol}%, Цена ±{price_tol}%: {count} предложений")

        # Покажем примеры предложений
        self.stdout.write("\nПримеры предложений в этом городе:")
        offers = MarketOffer.objects.filter(
            city=apartment.city,
            is_active=True
        )[:10]

        for i, offer in enumerate(offers, 1):
            self.stdout.write(f"{i}. {offer.rooms}-к, {offer.area} м², {offer.price} руб. - {offer.address[:30]}")