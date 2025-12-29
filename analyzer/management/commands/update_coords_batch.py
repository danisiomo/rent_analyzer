# analyzer/management/commands/update_coords_batch.py
from django.core.management.base import BaseCommand
from analyzer.models import MarketOffer
import time
import requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Пакетное обновление координат с улучшенной обработкой'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Размер пакета для обработки'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Пропускать записи с координатами'
        )
        parser.add_argument(
            '--city',
            type=str,
            help='Обновлять только для указанного города'
        )

    def geocode_with_retry(self, address: str, city_name: str, retries: int = 2) -> Optional[Tuple[float, float]]:
        """Геокодирование с повторными попытками"""
        # Форматирование адреса
        formatted = address

        # Замены для лучшего распознавания
        replacements = [
            ('ул.', 'улица'),
            ('пр.', 'проспект'),
            ('наб.', 'набережная'),
            ('ш.', 'шоссе'),
            ('б-р', 'бульвар'),
            ('пер.', 'переулок'),
            ('пл.', 'площадь'),
            ('ал.', 'аллея'),
        ]

        for old, new in replacements:
            formatted = formatted.replace(old, new)

        # Убираем лишние пробелы
        formatted = ' '.join(formatted.split())

        query = f"{formatted}, {city_name}, Россия"

        for attempt in range(retries):
            try:
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        'q': query,
                        'format': 'json',
                        'limit': 1,
                        'countrycodes': 'ru',
                        'accept-language': 'ru',
                        'dedupe': 1,
                    },
                    headers={
                        'User-Agent': f'RentAnalyzerPro-Batch/1.0 (batch-{attempt})'
                    },
                    timeout=20
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return float(data[0]['lat']), float(data[0]['lon'])

                elif response.status_code == 429:  # Too Many Requests
                    wait_time = 5 * (attempt + 1)  # Увеличиваем время ожидания
                    logger.warning(f"Rate limit, ждем {wait_time} сек...")
                    time.sleep(wait_time)
                    continue

            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут, попытка {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(3)
                continue
            except Exception as e:
                logger.error(f"Ошибка геокодирования: {e}")
                break

        return None

    def handle(self, *args, **options):
        delay = options['delay']
        batch_size = options['batch_size']
        skip_existing = options['skip_existing']
        city_filter = options['city']

        self.stdout.write("=" * 70)
        self.stdout.write("ПАКЕТНОЕ ОБНОВЛЕНИЕ КООРДИНАТ")
        self.stdout.write("=" * 70)

        # Формируем запрос
        offers_query = MarketOffer.objects.all()

        if city_filter:
            offers_query = offers_query.filter(city__name__iexact=city_filter)
            self.stdout.write(f"\n📍 ФИЛЬТР: только город {city_filter}")

        if skip_existing:
            offers_query = offers_query.filter(latitude__isnull=True) | offers_query.filter(longitude__isnull=True)
            self.stdout.write(f"⏭ ПРОПУСК: только без координат")

        total_offers = offers_query.count()
        self.stdout.write(f"\n📊 ВСЕГО ДЛЯ ОБРАБОТКИ: {total_offers} предложений")
        self.stdout.write(f"📦 РАЗМЕР ПАКЕТА: {batch_size}")
        self.stdout.write(f"⏱ ЗАДЕРЖКА: {delay} сек")
        self.stdout.write("-" * 70)

        if total_offers == 0:
            self.stdout.write(self.style.SUCCESS("✅ Нет предложений для обработки!"))
            return

        # Обработка пакетами
        updated_total = 0
        failed_total = 0
        batch_number = 0

        for i in range(0, total_offers, batch_size):
            batch_number += 1
            batch = list(offers_query[i:i + batch_size])

            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(f"ПАКЕТ #{batch_number}: {len(batch)} предложений")
            self.stdout.write(f"{'=' * 60}")

            updated_batch = 0
            failed_batch = 0

            for j, offer in enumerate(batch, 1):
                offer_num = i + j

                self.stdout.write(f"\n{offer_num:4d}/{total_offers}. {offer.address[:45]}...")
                self.stdout.write(f"     Город: {offer.city.name}")

                # Геокодируем
                lat, lon = self.geocode_with_retry(offer.address, offer.city.name)

                if lat and lon:
                    offer.latitude = lat
                    offer.longitude = lon
                    offer.save()
                    updated_batch += 1
                    updated_total += 1
                    self.stdout.write(self.style.SUCCESS(f"     ✓ {lat:.6f}, {lon:.6f}"))
                else:
                    # Пробуем альтернативный метод
                    if ',' in offer.address:
                        # Берем только улицу и дом
                        street_part = offer.address.split(',')[0].strip()
                        lat, lon = self.geocode_with_retry(street_part, offer.city.name)

                        if lat and lon:
                            offer.latitude = lat
                            offer.longitude = lon
                            offer.save()
                            updated_batch += 1
                            updated_total += 1
                            self.stdout.write(self.style.SUCCESS(f"     ✓ (упрощ.) {lat:.6f}, {lon:.6f}"))
                        else:
                            # Используем координаты города
                            if offer.city.latitude and offer.city.longitude:
                                offer.latitude = offer.city.latitude
                                offer.longitude = offer.city.longitude
                                offer.save()
                                self.stdout.write(f"     • Координаты города")
                            else:
                                self.stdout.write(self.style.WARNING(f"     ⚠ Не удалось"))
                                failed_batch += 1
                                failed_total += 1

                # Прогресс внутри пакета
                if j % 10 == 0:
                    progress = (offer_num / total_offers) * 100
                    self.stdout.write(f"     📊 Прогресс: {progress:.1f}%")

                # Пауза между запросами (кроме последнего)
                if j < len(batch):
                    time.sleep(delay)

            # Статистика по пакету
            self.stdout.write(f"\n📊 ПАКЕТ #{batch_number} ЗАВЕРШЕН:")
            self.stdout.write(f"   Обновлено: {updated_batch}")
            self.stdout.write(f"   Ошибок: {failed_batch}")

            # Пауза между пакетами (если не последний)
            if i + batch_size < total_offers:
                pause = delay * 3  # Удлиненная пауза между пакетами
                self.stdout.write(f"\n⏸ Пауза {pause} сек перед следующим пакетом...")
                time.sleep(pause)

        # Итоговая статистика
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        self.stdout.write(f"   Всего обработано: {total_offers} предложений")
        self.stdout.write(f"   Успешно обновлено: {updated_total}")
        self.stdout.write(f"   Не удалось: {failed_total}")

        if updated_total > 0:
            success_rate = (updated_total / total_offers) * 100
            self.stdout.write(f"   Успешность: {success_rate:.1f}%")

        # Показываем примеры обновленных координат
        self.stdout.write(f"\n📍 ПРИМЕРЫ ОБНОВЛЕННЫХ КООРДИНАТ:")

        import random
        recent_offers = MarketOffer.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by(
            '-id')[:10]

        if recent_offers:
            for offer in random.sample(list(recent_offers), min(5, len(recent_offers))):
                self.stdout.write(f"   {offer.address[:35]}...")
                self.stdout.write(f"     {offer.latitude:.6f}, {offer.longitude:.6f}")