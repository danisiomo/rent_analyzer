from django.core.management.base import BaseCommand
from utils.reliable_yandex_parser import reliable_parser
import json


class Command(BaseCommand):
    help = 'Тестирование надежного парсера'

    def add_arguments(self, parser):
        parser.add_argument('--city', default='Москва', help='Город')
        parser.add_argument('--limit', type=int, default=5, help='Лимит')

    def handle(self, *args, **options):
        city = options['city']
        limit = options['limit']

        self.stdout.write(f"Тестирование надежного парсера для {city}")
        self.stdout.write("=" * 60)

        offers = reliable_parser.get_rent_offers(city, limit=limit)

        self.stdout.write(f"Получено предложений: {len(offers)}")
        self.stdout.write("Источники данных:")

        sources = {}
        for offer in offers:
            source = offer['source']
            sources[source] = sources.get(source, 0) + 1

        for source, count in sources.items():
            quality = reliable_parser._assess_data_quality(source)
            self.stdout.write(f"  {source}: {count} предложений (качество: {quality})")

        if offers:
            self.stdout.write("\nПримеры:")
            for i, offer in enumerate(offers[:3], 1):
                self.stdout.write(f"\n{i}. {offer['address'][:40]}...")
                self.stdout.write(f"   Комнат: {offer['rooms']}, Площадь: {offer['area']} м²")
                self.stdout.write(f"   Цена: {offer['price']:,.0f} руб.")
                self.stdout.write(f"   Источник: {offer['source']}")