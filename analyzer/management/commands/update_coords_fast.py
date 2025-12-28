
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer, Apartment
import time
import requests


class Command(BaseCommand):
    help = 'Быстрое обновление координат'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Лимит записей (0 = все)'
        )

    def _geocode_simple(self, address: str, city: str = None):
        """Простое геокодирование"""
        # Форматируем адрес
        query = address.replace('ул.', 'улица').replace('пр.', 'проспект')
        query = query.replace(', ', ' ')
        if city:
            query = f"{query}, {city}, Россия"
        else:
            query = f"{query}, Россия"

        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'ru'},
                headers={'User-Agent': 'RentAnalyzer/1.0'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])

        except Exception as e:
            self.stdout.write(f"  Ошибка: {e}")

        return None, None

    def handle(self, *args, **options):
        delay = options['delay']
        limit = options['limit']

        self.stdout.write("Быстрое обновление координат...")

        # Обновляем рыночные предложения
        offers = MarketOffer.objects.all()
        if limit > 0:
            offers = offers[:limit]

        self.stdout.write(f"Найдено предложений: {offers.count()}")

        updated = 0
        failed = 0

        for i, offer in enumerate(offers, 1):
            self.stdout.write(f"\n{i}. {offer.address}")
            self.stdout.write(f"   Город: {offer.city.name}")

            try:
                # Геокодируем
                lat, lon = self._geocode_simple(offer.address, offer.city.name)

                if lat and lon:
                    offer.latitude = lat
                    offer.longitude = lon
                    offer.save()

                    self.stdout.write(
                        self.style.SUCCESS(f"   ✓ Координаты: {lat:.6f}, {lon:.6f}")
                    )
                    updated += 1
                else:
                    # Используем координаты города
                    if offer.city.latitude and offer.city.longitude:
                        offer.latitude = offer.city.latitude
                        offer.longitude = offer.city.longitude
                        offer.save()
                        self.stdout.write(f"   • Использованы координаты города")
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠ Не удалось геокодировать"))
                        failed += 1

                # Пауза
                if i < len(offers):
                    time.sleep(delay)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ✗ Исключение: {e}"))
                failed += 1

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(f"ГОТОВО! Обновлено: {updated}, Не удалось: {failed}")