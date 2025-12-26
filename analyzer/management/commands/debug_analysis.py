from django.core.management.base import BaseCommand
from analyzer.models import Apartment
from utils.analyzer import ApartmentAnalyzer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отладка создания графиков анализа'

    def add_arguments(self, parser):
        parser.add_argument('--apartment_id', type=int, help='ID квартиры')

    def handle(self, *args, **options):
        apartment_id = options.get('apartment_id')

        if not apartment_id:
            # Берем первую квартиру пользователя
            from django.contrib.auth.models import User
            user = User.objects.first()
            if user:
                apartment = Apartment.objects.filter(user=user).first()
                if apartment:
                    apartment_id = apartment.id

        if not apartment_id:
            self.stdout.write(self.style.ERROR("Нет квартир для анализа"))
            return

        apartment = Apartment.objects.get(id=apartment_id)

        self.stdout.write(f"Анализ квартиры: {apartment.address}")
        self.stdout.write(f"Площадь: {apartment.area} м², Комнат: {apartment.rooms}")
        self.stdout.write(f"Цена: {apartment.desired_price} руб.")
        self.stdout.write(f"Город: {apartment.city.name}")
        self.stdout.write("=" * 60)

        # Запускаем анализ
        analyzer = ApartmentAnalyzer(apartment)
        similar_offers = analyzer.find_similar_offers(max_results=50)

        self.stdout.write(f"Найдено похожих предложений: {len(similar_offers)}")

        if similar_offers:
            self.stdout.write("Первые 3 предложения:")
            for i, offer in enumerate(similar_offers[:3], 1):
                self.stdout.write(f"{i}. {offer.address[:30]}... - {offer.price} руб., {offer.area} м²")

        # Проверяем доступность графиков
        self.stdout.write("\nПроверка доступности графиков...")

        try:
            from utils.charts import chart_generator
            CHARTS_AVAILABLE = True
            self.stdout.write(self.style.SUCCESS("✓ Chart generator доступен"))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"✗ Chart generator не доступен: {e}"))
            CHARTS_AVAILABLE = False

        # Тестируем графики если доступны
        if CHARTS_AVAILABLE and len(similar_offers) >= 3:
            self.stdout.write("Создаем графики...")

            # 1. Распределение цен
            try:
                chart1 = chart_generator.create_price_distribution_chart(
                    similar_offers,
                    apartment_price=float(apartment.desired_price),
                    title="Тест: Распределение цен"
                )
                if chart1:
                    self.stdout.write(self.style.SUCCESS("✓ Гистограмма создана успешно"))
                    # Проверяем длину base64 строки
                    self.stdout.write(f"  Длина base64: {len(chart1)} символов")
                else:
                    self.stdout.write(self.style.WARNING("⚠ Гистограмма вернула пустую строку"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Ошибка гистограммы: {e}"))
                import traceback
                self.stdout.write(traceback.format_exc())

            # 2. Простой scatter plot
            try:
                chart2 = chart_generator.create_price_vs_area_scatter(
                    similar_offers,
                    apartment_area=float(apartment.area),
                    apartment_price=float(apartment.desired_price),
                    title="Тест: Цена vs Площадь"
                )
                if chart2:
                    self.stdout.write(self.style.SUCCESS("✓ Scatter plot создан успешно"))
                    self.stdout.write(f"  Длина base64: {len(chart2)} символов")
                else:
                    self.stdout.write(self.style.WARNING("⚠ Scatter plot вернул пустую строку"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Ошибка scatter plot: {e}"))

        else:
            if not CHARTS_AVAILABLE:
                self.stdout.write(self.style.WARNING("⚠ Chart generator не доступен"))
            if len(similar_offers) < 3:
                self.stdout.write(self.style.WARNING(f"⚠ Мало предложений для графиков: {len(similar_offers)}"))

        # Проверяем данные предложений
        self.stdout.write("\nПроверка данных предложений:")
        if similar_offers:
            for i, offer in enumerate(similar_offers[:5]):
                self.stdout.write(f"{i + 1}. ID: {offer.id}, Цена: {offer.price}, Площадь: {offer.area}, "
                                  f"Комнат: {offer.rooms}, Город: {offer.city.name}")