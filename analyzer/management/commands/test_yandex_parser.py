from django.core.management.base import BaseCommand
from utils.yandex_realty_parser import yandex_realty_parser
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирование парсера Яндекс.Недвижимость'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            default='Москва',
            help='Город для тестирования'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Количество предложений для парсинга'
        )

    def handle(self, *args, **options):
        city = options['city']
        limit = options['limit']

        self.stdout.write(f"Тестирование парсера Яндекс.Недвижимость для города: {city}")
        self.stdout.write("=" * 60)

        if not yandex_realty_parser.is_available:
            self.stdout.write(self.style.ERROR("✗ Библиотека yandex-realty-parser не установлена!"))
            self.stdout.write("Установите: pip install yandex-realty-parser")
            return

        self.stdout.write(self.style.SUCCESS("✓ Библиотека доступна"))

        # Тестируем подключение
        self.stdout.write("Тестирование подключения...")
        if yandex_realty_parser.test_connection():
            self.stdout.write(self.style.SUCCESS("✓ Подключение успешно"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Подключение не удалось"))

        # Парсим данные
        self.stdout.write(f"\nПарсинг данных для {city}...")
        offers = yandex_realty_parser.get_rent_offers(city, limit=limit)

        if offers:
            self.stdout.write(self.style.SUCCESS(f"✓ Успешно получено {len(offers)} предложений"))
            self.stdout.write("\nПримеры предложений:")
            self.stdout.write("-" * 60)

            for i, offer in enumerate(offers[:3], 1):
                self.stdout.write(f"\n{i}. {offer['address'][:50]}...")
                self.stdout.write(f"   Комнат: {offer['rooms']}, Площадь: {offer['area']} м²")
                self.stdout.write(f"   Цена: {offer['price']:,.0f} руб. ({offer['price_per_sqm']:.0f} руб./м²)")
                self.stdout.write(f"   Источник: {offer['source']}")

            # Статистика
            prices = [o['price'] for o in offers]
            areas = [o['area'] for o in offers]

            if prices and areas:
                avg_price = sum(prices) / len(prices)
                avg_area = sum(areas) / len(areas)
                avg_price_per_sqm = avg_price / avg_area if avg_area > 0 else 0

                self.stdout.write("\n" + "=" * 60)
                self.stdout.write("СТАТИСТИКА:")
                self.stdout.write(f"Средняя цена: {avg_price:,.0f} руб.")
                self.stdout.write(f"Средняя площадь: {avg_area:.1f} м²")
                self.stdout.write(f"Средняя цена за м²: {avg_price_per_sqm:.0f} руб.")

        else:
            self.stdout.write(self.style.WARNING("⚠ Не удалось получить данные"))
            self.stdout.write("\nВозможные причины:")
            self.stdout.write("1. Сайт Яндекс.Недвижимость изменил структуру")
            self.stdout.write("2. Проблемы с подключением к интернету")
            self.stdout.write("3. Город не поддерживается парсером")
            self.stdout.write("\nСистема продолжит работу с аналитическими данными")