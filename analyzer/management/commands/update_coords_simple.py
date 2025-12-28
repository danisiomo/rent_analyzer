
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer, Apartment
import time
import requests


class Command(BaseCommand):
    help = 'Простое обновление координат'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами'
        )

    def geocode_address(self, address: str, city: str) -> tuple:
        """Простое геокодирование одного адреса"""
        # Форматируем адрес
        query = address.replace('ул.', 'улица').replace('пр.', 'проспект')
        query = query.replace(', ', ' ')
        query = f"{query}, {city}, Россия"

        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'ru',
                },
                headers={'User-Agent': 'RentAnalyzer/1.0'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])

        except Exception as e:
            self.stdout.write(f"    Ошибка запроса: {e}")

        return None, None

    def handle(self, *args, **options):
        delay = options['delay']

        self.stdout.write("Простое обновление координат...")
        self.stdout.write(f"Задержка между запросами: {delay} сек")

        # Обновляем рыночные предложения
        offers = MarketOffer.objects.all()

        self.stdout.write(f"\nОбновление рыночных предложений ({offers.count()} шт)...")

        updated = 0
        failed = 0

        for i, offer in enumerate(offers, 1):
            self.stdout.write(f"\n{i}. {offer.address}")
            self.stdout.write(f"   Город: {offer.city.name}")

            # Геокодируем
            lat, lon = self.geocode_address(offer.address, offer.city.name)

            if lat and lon:
                offer.latitude = lat
                offer.longitude = lon
                offer.save()
                self.stdout.write(self.style.SUCCESS(f"   ✓ Координаты: {lat:.6f}, {lon:.6f}"))
                updated += 1
            else:
                # Используем координаты города
                if offer.city.latitude and offer.city.longitude:
                    offer.latitude = offer.city.latitude
                    offer.longitude = offer.city.longitude
                    offer.save()
                    self.stdout.write(f"   • Использованы координаты города")
                else:
                    self.stdout.write(self.style.WARNING(f"   ⚠ Не удалось получить координаты"))
                    failed += 1

            # Пауза
            if i < len(offers):
                time.sleep(delay)

        # Обновляем квартиры
        self.stdout.write(f"\n\nОбновление квартир пользователей...")
        apartments = Apartment.objects.all()

        for i, apartment in enumerate(apartments, 1):
            self.stdout.write(f"\n{i}. {apartment.address}")

            lat, lon = self.geocode_address(apartment.address, apartment.city.name)

            if lat and lon:
                apartment.latitude = lat
                apartment.longitude = lon
                apartment.save()
                self.stdout.write(self.style.SUCCESS(f"   ✓ Координаты: {lat:.6f}, {lon:.6f}"))
            else:
                if apartment.city.latitude and apartment.city.longitude:
                    apartment.latitude = apartment.city.latitude
                    apartment.longitude = apartment.city.longitude
                    apartment.save()
                    self.stdout.write(f"   • Использованы координаты города")

            if i < len(apartments):
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write("ГОТОВО! Координаты обновлены.")
        self.stdout.write(f"Успешно: {updated}, Не удалось: {failed}")