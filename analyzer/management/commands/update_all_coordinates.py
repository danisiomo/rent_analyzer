from django.core.management.base import BaseCommand
from analyzer.models import City, MarketOffer
from utils.geocoder import geocoder
import logging
from django.core.cache import cache
logger = logging.getLogger(__name__)
import time

class Command(BaseCommand):
    help = 'Массовое обновление координат для всех городов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,  # Уменьшаем размер батча
            help='Размер батча для обработки'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами (секунды)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        delay = options['delay']

        # Очищаем кэш
        cache.clear()
        self.stdout.write("Кэш геокодирования очищен")

        total_offers = MarketOffer.objects.count()
        self.stdout.write(f"Всего предложений в базе: {total_offers}")

        # Обрабатываем пачками
        processed = 0
        updated = 0
        errors = 0

        batch_number = 0

        while processed < total_offers:
            batch_number += 1
            self.stdout.write(f"\n=== Батч #{batch_number} ===")

            # Берем следующую пачку
            offers = MarketOffer.objects.all().order_by('id')[processed:processed + batch_size]
            batch_count = offers.count()

            if batch_count == 0:
                break

            self.stdout.write(f"Обработка {batch_count} предложений...")

            for i, offer in enumerate(offers, 1):
                try:
                    old_lat = offer.latitude
                    old_lon = offer.longitude

                    # Очищаем координаты
                    offer.latitude = None
                    offer.longitude = None

                    # Сохраняем
                    offer.save()

                    # Проверяем изменение
                    if old_lat != offer.latitude or old_lon != offer.longitude:
                        updated += 1
                        self.stdout.write(f"  [{i}/{batch_count}] ✓ {offer.address}: обновлено")
                    else:
                        self.stdout.write(f"  [{i}/{batch_count}] • {offer.address}: без изменений")

                    processed += 1

                    # Задержка между запросами
                    if i < batch_count:
                        time.sleep(delay)

                except Exception as e:
                    errors += 1
                    self.stdout.write(f"  [{i}/{batch_count}] ✗ Ошибка: {e}")
                    continue

            self.stdout.write(f"Обработано: {processed}/{total_offers}")
            self.stdout.write(f"Обновлено: {updated}, Ошибок: {errors}")

            # Пауза между батчами
            if processed < total_offers:
                self.stdout.write(f"Пауза {delay * 2} секунд перед следующим батчем...")
                time.sleep(delay * 2)

        self.stdout.write(
            self.style.SUCCESS(f"\n=== ЗАВЕРШЕНО ===")
        )
        self.stdout.write(f"Всего обработано: {processed}")
        self.stdout.write(f"Обновлено: {updated}")
        self.stdout.write(f"Ошибок: {errors}")