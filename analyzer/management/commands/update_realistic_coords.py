# analyzer/management/commands/update_realistic_coords.py
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer, Apartment
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Обновление координат для реалистичных данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами (секунды)'
        )

    def handle(self, *args, **options):
        delay = options['delay']

        self.stdout.write("Обновление координат для реалистичных данных...")

        # Обновляем рыночные предложения
        offers = MarketOffer.objects.filter(latitude__isnull=True) | MarketOffer.objects.filter(longitude__isnull=True)

        self.stdout.write(f"Найдено предложений без координат: {offers.count()}")

        updated = 0
        errors = 0

        for i, offer in enumerate(offers, 1):
            try:
                self.stdout.write(f"\n{i}. {offer.address}")
                self.stdout.write(f"   Город: {offer.city.name}")

                # Очищаем координаты для принудительного перегеокодирования
                old_lat = offer.latitude
                old_lon = offer.longitude

                offer.latitude = None
                offer.longitude = None

                # Сохраняем
                offer.save()

                if old_lat != offer.latitude or old_lon != offer.longitude:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✓ Обновлено: {offer.latitude:.6f}, {offer.longitude:.6f}"
                        )
                    )
                    updated += 1
                else:
                    self.stdout.write(f"   • Координаты не изменились")

                # Пауза для rate limit
                if i < len(offers):
                    self.stdout.write(f"   ⏳ Ждем {delay} сек...")
                    time.sleep(delay)

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"   ✗ Ошибка: {e}"))
                continue

        # Обновляем квартиры пользователей
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Обновление квартир пользователей...")

        apartments = Apartment.objects.filter(latitude__isnull=True) | Apartment.objects.filter(longitude__isnull=True)

        self.stdout.write(f"Найдено квартир без координат: {apartments.count()}")

        for i, apartment in enumerate(apartments, 1):
            try:
                self.stdout.write(f"\n{i}. {apartment.address}")

                apartment.latitude = None
                apartment.longitude = None
                apartment.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"   ✓ Координаты: {apartment.latitude:.6f}, {apartment.longitude:.6f}"
                    )
                )

                if i < len(apartments):
                    time.sleep(delay)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ✗ Ошибка: {e}"))

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write("ГОТОВО!")
        self.stdout.write(f"Обновлено предложений: {updated}")
        self.stdout.write(f"Ошибок: {errors}")