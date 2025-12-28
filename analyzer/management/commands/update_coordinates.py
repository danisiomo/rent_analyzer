from django.core.cache import CacheKeyWarning
from django.core.management.base import BaseCommand
from analyzer.models import Apartment, MarketOffer
from utils.geocoder import geocoder
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Обновление координат для квартир и рыночных предложений'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['apartments', 'offers', 'all'],
            default='all',
            help='Тип объектов для обновления'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Максимальное количество объектов для обновления'
        )

    def handle(self, *args, **options):
        obj_type = options['type']
        limit = options['limit']

        updated_count = 0
        failed_count = 0

        if obj_type in ['offers', 'all']:
            self.stdout.write("Обновление координат рыночных предложений...")

            # Игнорируем предупреждения о кэше
            import warnings
            warnings.filterwarnings("ignore", category=CacheKeyWarning)

            offers = MarketOffer.objects.all().order_by('-parsed_date')[:limit]

            for offer in offers:
                try:
                    # Очищаем кэш для этого адреса
                    from django.core.cache import cache
                    cache_key = f"geocode_{offer.address}_{offer.city.name}"
                    cache.delete(cache_key)

                    # Сохраняем старые координаты
                    old_lat = offer.latitude
                    old_lon = offer.longitude

                    # Очищаем координаты
                    offer.latitude = None
                    offer.longitude = None

                    # Сохраняем (вызовет геокодирование)
                    offer.save()

                    # Проверяем, изменились ли координаты
                    if old_lat != offer.latitude or old_lon != offer.longitude:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Обновлено предложение {offer.id}: "
                                f"{old_lat},{old_lon} -> {offer.latitude},{offer.longitude}"
                            )
                        )
                    else:
                        self.stdout.write(f"  • Предложение {offer.id} без изменений")

                    updated_count += 1

                    # Пауза между запросами
                    time.sleep(0.1)

                except Exception as e:
                    failed_count += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ Ошибка предложения {offer.id}: {e}"))