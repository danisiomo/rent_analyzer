from django.core.management.base import BaseCommand
from django.utils import timezone
from analyzer.models import City
from utils.real_estate_api import data_collector
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Обновление рыночных данных о ценах на аренду'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            help='Название конкретного города для обновления'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Количество предложений для каждого города'
        )

    def handle(self, *args, **options):
        city_name = options['city']
        limit = options['limit']

        if city_name:
            cities = City.objects.filter(name__icontains=city_name)
        else:
            cities = City.objects.all()

        total_saved = 0

        for city in cities:
            self.stdout.write(f"Обновление данных для {city.name}...")
            try:
                saved = data_collector.update_market_data(city, limit)
                total_saved += saved
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {city.name}: добавлено {saved} предложений")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {city.name}: ошибка - {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nОбновление завершено! Всего добавлено {total_saved} предложений"
            )
        )