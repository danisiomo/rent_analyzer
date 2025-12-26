from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer
from utils.geocoder import geocoder
import time


class Command(BaseCommand):
    help = 'Геокодирование существующих рыночных предложений'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Лимит предложений')

    def handle(self, *args, **options):
        limit = options['limit']

        # Находим предложения без координат
        offers = MarketOffer.objects.filter(
            latitude__isnull=True,
            longitude__isnull=True,
            is_active=True
        )[:limit]

        self.stdout.write(f"Найдено предложений без координат: {offers.count()}")

        success = 0
        failed = 0

        for offer in offers:
            self.stdout.write(f"Геокодирование: {offer.address}...")

            try:
                result = geocoder.geocode(offer.address, offer.city.name if offer.city else None)

                if result:
                    offer.latitude = result['lat']
                    offer.longitude = result['lon']
                    offer.save()

                    success += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Координаты: {offer.latitude}, {offer.longitude}"
                    ))
                else:
                    # Устанавливаем координаты города как fallback
                    if offer.city and hasattr(offer.city, 'latitude') and offer.city.latitude:
                        offer.latitude = offer.city.latitude
                        offer.longitude = offer.city.longitude
                        offer.save()
                        success += 1
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠ Использованы координаты города"
                        ))
                    else:
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f"  ✗ Не удалось геокодировать"
                        ))

                # Задержка для rate limit
                time.sleep(1.5)

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Ошибка: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nГотово! Успешно: {success}, Не удалось: {failed}"))