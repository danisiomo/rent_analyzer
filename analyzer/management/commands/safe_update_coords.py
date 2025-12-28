
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer, Apartment
import time


class Command(BaseCommand):
    help = 'Безопасное обновление координат'

    def handle(self, *args, **options):
        self.stdout.write("Начало безопасного обновления координат...")

        # Обновляем рыночные предложения
        offers = MarketOffer.objects.all()[:20]  # Только 20 для теста

        for i, offer in enumerate(offers, 1):
            try:
                self.stdout.write(f"\n{i}. {offer.address}")

                # Очищаем координаты
                offer.latitude = None
                offer.longitude = None

                # Сохраняем
                offer.save()

                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Координаты: {offer.latitude}, {offer.longitude}")
                )

                # Пауза
                if i < len(offers):
                    time.sleep(2)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Ошибка: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS("\nГотово!"))