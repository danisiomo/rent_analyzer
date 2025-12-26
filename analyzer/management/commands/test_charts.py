from django.core.management.base import BaseCommand
from analyzer.models import Apartment, MarketOffer, City
from django.contrib.auth.models import User
from utils.charts import chart_generator
import base64
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Тестирование генерации графиков'

    def handle(self, *args, **options):
        self.stdout.write("Тестирование генерации графиков...")
        self.stdout.write("=" * 60)

        # Создаем тестовые данные если нет
        user, _ = User.objects.get_or_create(username='test_user')
        city, _ = City.objects.get_or_create(
            name='Тестовый город',
            defaults={'avg_price_per_sqm': 1500, 'population': 100000}
        )

        # Создаем тестовую квартиру
        apartment, _ = Apartment.objects.get_or_create(
            user=user,
            city=city,
            defaults={
                'address': 'Тестовый адрес, 1',
                'area': 50.0,
                'rooms': 2,
                'floor': 5,
                'total_floors': 10,
                'desired_price': 50000,
            }
        )

        # Получаем или создаем тестовые предложения
        offers = MarketOffer.objects.filter(city=city, rooms=2)[:20]

        if not offers.exists():
            self.stdout.write("Создаем тестовые предложения...")
            for i in range(20):
                MarketOffer.objects.create(
                    city=city,
                    source='test',
                    address=f'Тестовая улица, {i}',
                    area=40 + i,
                    rooms=2,
                    price=40000 + i * 2000,
                    is_active=True
                )
            offers = MarketOffer.objects.filter(city=city, rooms=2)

        self.stdout.write(f"Найдено предложений: {offers.count()}")

        # Тестируем графики
        try:
            # 1. Распределение цен
            self.stdout.write("\n1. Тестируем гистограмму распределения цен...")
            chart1 = chart_generator.create_price_distribution_chart(
                offers,
                apartment_price=float(apartment.desired_price),
                title="Тест: Распределение цен"
            )

            if chart1:
                self.save_test_chart(chart1, 'price_distribution.png')
                self.stdout.write(self.style.SUCCESS("✓ Гистограмма создана успешно"))
            else:
                self.stdout.write(self.style.WARNING("⚠ Не удалось создать гистограмму"))

            # 2. Scatter plot
            self.stdout.write("\n2. Тестируем scatter plot...")
            chart2 = chart_generator.create_price_vs_area_scatter(
                offers,
                apartment_area=float(apartment.area),
                apartment_price=float(apartment.desired_price),
                title="Тест: Цена vs Площадь"
            )

            if chart2:
                self.save_test_chart(chart2, 'price_vs_area.png')
                self.stdout.write(self.style.SUCCESS("✓ Scatter plot создан успешно"))
            else:
                self.stdout.write(self.style.WARNING("⚠ Не удалось создать scatter plot"))

            # 3. Дашборд
            self.stdout.write("\n3. Тестируем комплексный дашборд...")
            market_stats = {
                'avg_price': 55000,
                'median_price': 52000,
                'min_price': 40000,
                'max_price': 70000
            }

            charts = chart_generator.create_market_analysis_dashboard(
                apartment, offers, market_stats
            )

            if charts:
                self.stdout.write(self.style.SUCCESS(f"✓ Дашборд создан: {len(charts)} графиков"))
                for chart_name in charts.keys():
                    self.stdout.write(f"  - {chart_name}")
            else:
                self.stdout.write(self.style.WARNING("⚠ Не удалось создать дашборд"))

            self.stdout.write(self.style.SUCCESS("\n✓ Тестирование графиков завершено!"))
            self.stdout.write("Проверьте папку media/test_charts/ для просмотра графиков")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Ошибка: {e}"))

    def save_test_chart(self, chart_base64: str, filename: str):
        """Сохраняет тестовый график в файл"""
        try:
            # Создаем папку если нет
            os.makedirs('media/test_charts', exist_ok=True)

            # Декодируем и сохраняем
            chart_data = base64.b64decode(chart_base64)
            filepath = f'media/test_charts/{filename}'

            with open(filepath, 'wb') as f:
                f.write(chart_data)

            return filepath
        except Exception as e:
            self.stdout.write(f"Ошибка сохранения графика: {e}")
            return None