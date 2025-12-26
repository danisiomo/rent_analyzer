from django.core.management.base import BaseCommand
from analyzer.models import City
from utils.geocoder import geocoder
import time


class Command(BaseCommand):
    help = 'Обновление координат городов'

    def handle(self, *args, **options):
        cities = City.objects.filter(latitude__isnull=True) | City.objects.filter(longitude__isnull=True)

        self.stdout.write(f"Найдено городов без координат: {cities.count()}")

        for city in cities:
            self.stdout.write(f"Обновление координат для {city.name}...")

            try:
                # Геокодируем название города
                result = geocoder.geocode(city.name)

                if result:
                    city.latitude = result['lat']
                    city.longitude = result['lon']
                    city.save()

                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Координаты обновлены: {city.latitude}, {city.longitude}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  ✗ Не удалось получить координаты"
                    ))

                # Задержка для соблюдения rate limit
                time.sleep(1.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Ошибка: {e}"))

        self.stdout.write(self.style.SUCCESS("Обновление завершено!"))