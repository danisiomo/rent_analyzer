
from django.core.management.base import BaseCommand
from utils.geocoder_final_working import geocoder
import time


class Command(BaseCommand):
    help = 'Тестирование простого геокодировщика'

    def handle(self, *args, **options):
        test_cases = [
            ("ул. Садовая, 4", "Екатеринбург"),
            ("ул. Ленина, 85", "Екатеринбург"),
            ("ул. Кирова, 116", "Екатеринбург"),
            ("ул. Пушкина, 148", "Санкт-Петербург"),
            ("Санкт-Петербург, Василеостровский, ул. Пушкина, 148", None),
            ("ул. Советская, 45", "Санкт-Петербург"),
            ("пр. Победы, 31", "Санкт-Петербург"),  # Этот был проблемным
        ]

        self.stdout.write("=" * 80)
        self.stdout.write("ТЕСТИРОВАНИЕ ПРОСТОГО ГЕОКОДЕРА")
        self.stdout.write("=" * 80)

        for address, city in test_cases:
            self.stdout.write(f"\nАдрес: {address}")
            if city:
                self.stdout.write(f"Город: {city}")

            result = geocoder.geocode(address, city)

            if result:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Найдено: {result['lat']}, {result['lon']}"
                    )
                )
                display = result.get('display_name', '')
                if len(display) > 100:
                    display = display[:100] + "..."
                self.stdout.write(f"Адрес: {display}")
            else:
                self.stdout.write(self.style.ERROR("✗ Не найдено"))

            # Пауза между запросами
            if test_cases.index((address, city)) < len(test_cases) - 1:
                time.sleep(1.5)