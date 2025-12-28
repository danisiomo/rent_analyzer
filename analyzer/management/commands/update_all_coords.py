# analyzer/management/commands/update_all_coords.py
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer, Apartment
import time
import requests
from typing import Optional, Tuple


class Command(BaseCommand):
    help = 'Массовое обновление координат для всей базы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами (секунды)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничение количества записей (0 = все)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Пропускать записи с уже установленными координатами'
        )

    def geocode_simple(self, address: str, city_name: str) -> Optional[Tuple[float, float]]:
        """Простое геокодирование одного адреса"""
        # Форматируем адрес
        formatted = address.replace('ул.', 'улица').replace('пр.', 'проспект')
        formatted = formatted.replace(' наб.', ' набережная').replace(' ш.', ' шоссе')
        formatted = formatted.replace(', ', ' ')

        query = f"{formatted}, {city_name}, Россия"

        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'ru',
                    'accept-language': 'ru',
                },
                headers={'User-Agent': 'RentAnalyzerPro/1.0'},
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['lat']), float(data[0]['lon'])

        except requests.exceptions.Timeout:
            self.stdout.write(f"    ⏱ Таймаут")
        except Exception as e:
            self.stdout.write(f"    ⚠ Ошибка: {str(e)[:50]}")

        return None

    def handle(self, *args, **options):
        delay = options['delay']
        limit = options['limit']
        skip_existing = options['skip_existing']

        self.stdout.write("=" * 70)
        self.stdout.write("МАССОВОЕ ОБНОВЛЕНИЕ КООРДИНАТ")
        self.stdout.write("=" * 70)

        # Обновляем рыночные предложения
        offers_query = MarketOffer.objects.all()

        if skip_existing:
            offers_query = offers_query.filter(latitude__isnull=True) | offers_query.filter(longitude__isnull=True)

        if limit > 0:
            offers_query = offers_query[:limit]

        offers = list(offers_query)

        self.stdout.write(f"\n📊 РЫНОЧНЫЕ ПРЕДЛОЖЕНИЯ: {len(offers)} шт")
        self.stdout.write(f"⏱ Задержка: {delay} сек между запросами")
        self.stdout.write("-" * 70)

        updated_offers = 0
        failed_offers = 0

        for i, offer in enumerate(offers, 1):
            self.stdout.write(f"\n{i:3d}. {offer.address}")
            self.stdout.write(f"     Город: {offer.city.name}")

            # Геокодируем
            lat, lon = self.geocode_simple(offer.address, offer.city.name)

            if lat and lon:
                offer.latitude = lat
                offer.longitude = lon
                offer.save()
                updated_offers += 1
                self.stdout.write(self.style.SUCCESS(f"     ✓ Координаты: {lat:.6f}, {lon:.6f}"))
            else:
                # Используем координаты города
                if offer.city.latitude and offer.city.longitude:
                    offer.latitude = offer.city.latitude
                    offer.longitude = offer.city.longitude
                    offer.save()
                    self.stdout.write(f"     • Использованы координаты города")
                else:
                    self.stdout.write(self.style.WARNING(f"     ⚠ Не удалось получить координаты"))
                    failed_offers += 1

            # Прогресс
            if i % 10 == 0:
                self.stdout.write(f"\n📈 Прогресс: {i}/{len(offers)} ({i / len(offers) * 100:.1f}%)")

            # Пауза
            if i < len(offers):
                time.sleep(delay)

        # Обновляем квартиры пользователей
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("🏠 КВАРТИРЫ ПОЛЬЗОВАТЕЛЕЙ")
        self.stdout.write("-" * 70)

        apartments_query = Apartment.objects.all()

        if skip_existing:
            apartments_query = apartments_query.filter(latitude__isnull=True) | apartments_query.filter(
                longitude__isnull=True)

        apartments = list(apartments_query)

        updated_apartments = 0

        for i, apartment in enumerate(apartments, 1):
            self.stdout.write(f"\n{i:3d}. {apartment.address}")
            self.stdout.write(f"     Город: {apartment.city.name}")

            lat, lon = self.geocode_simple(apartment.address, apartment.city.name)

            if lat and lon:
                apartment.latitude = lat
                apartment.longitude = lon
                apartment.save()
                updated_apartments += 1
                self.stdout.write(self.style.SUCCESS(f"     ✓ Координаты: {lat:.6f}, {lon:.6f}"))
            else:
                if apartment.city.latitude and apartment.city.longitude:
                    apartment.latitude = apartment.city.latitude
                    apartment.longitude = apartment.city.longitude
                    apartment.save()
                    self.stdout.write(f"     • Использованы координаты города")

            if i < len(apartments):
                time.sleep(delay)

        # Итоговая статистика
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        self.stdout.write(f"   Рыночные предложения: {updated_offers} обновлено, {failed_offers} ошибок")
        self.stdout.write(f"   Квартиры пользователей: {updated_apartments} обновлено")

        total_updated = updated_offers + updated_apartments
        self.stdout.write(f"   ВСЕГО ОБНОВЛЕНО: {total_updated} объектов")

        # Показываем примеры разных координат
        self.stdout.write(f"\n📍 ПРИМЕРЫ КООРДИНАТ:")

        import random
        sample_offers = list(MarketOffer.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True))
        if sample_offers:
            for offer in random.sample(sample_offers, min(3, len(sample_offers))):
                self.stdout.write(f"   {offer.address[:30]}...: {offer.latitude:.6f}, {offer.longitude:.6f}")