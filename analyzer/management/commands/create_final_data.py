
from django.core.management.base import BaseCommand
from analyzer.models import City, MarketOffer, Apartment
from django.contrib.auth.models import User
import random
from decimal import Decimal
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Финальное создание тестовых данных'

    def handle(self, *args, **options):
        self.stdout.write("Создание финальных тестовых данных...")

        # Создаем или получаем города
        cities = {}

        # Екатеринбург
        city, created = City.objects.get_or_create(
            name='Екатеринбург',
            defaults={
                'latitude': 56.8389,
                'longitude': 60.6057,
                'avg_price_per_sqm': Decimal('85000.00'),
                'population': 1500000,
            }
        )
        cities['Екатеринбург'] = city
        self.stdout.write(f"{'Создан' if created else 'Найден'} город: {city.name}")

        # Москва
        city, created = City.objects.get_or_create(
            name='Москва',
            defaults={
                'latitude': 55.7558,
                'longitude': 37.6173,
                'avg_price_per_sqm': Decimal('250000.00'),
                'population': 12000000,
            }
        )
        cities['Москва'] = city
        self.stdout.write(f"{'Создан' if created else 'Найден'} город: {city.name}")

        # Санкт-Петербург
        city, created = City.objects.get_or_create(
            name='Санкт-Петербург',
            defaults={
                'latitude': 59.9343,
                'longitude': 30.3351,
                'avg_price_per_sqm': Decimal('150000.00'),
                'population': 5000000,
            }
        )
        cities['Санкт-Петербург'] = city
        self.stdout.write(f"{'Создан' if created else 'Найден'} город: {city.name}")

        # Удаляем старые предложения
        MarketOffer.objects.all().delete()
        Apartment.objects.all().delete()
        self.stdout.write("Старые предложения удалены")

        # РЕАЛЬНЫЕ АДРЕСА ЕКАТЕРИНБУРГА (проверенные)
        ekb_addresses = [
            "ул. Ленина, 50",
            "ул. Малышева, 31",
            "пр. Ленина, 24а",
            "ул. 8 Марта, 8",
            "ул. Луначарского, 81",
            "ул. Вильгельма де Геннина, 49",
            "ул. Фрезеровщиков, 54",
            "ул. Белореченская, 24",
            "ул. Кирова, 55",
            "ул. Бардина, 28",
        ]

        # Создаем рыночные предложения для Екатеринбурга
        self.stdout.write("\nСоздание рыночных предложений для Екатеринбурга...")

        city = cities['Екатеринбург']
        sources = ['avito', 'cian', 'yandex']

        for i, address in enumerate(ekb_addresses):
            # Генерируем параметры
            rooms = random.choice([1, 2, 3])
            area = Decimal(str(round(random.uniform(30.0, 90.0), 1)))

            # Базовая цена
            base_price = 20000  # float для расчетов

            # Корректировка по адресу (центр дороже)
            if any(central in address for central in ['Ленина', 'Малышева', '8 Марта']):
                price_multiplier = random.uniform(1.3, 1.8)
            else:
                price_multiplier = random.uniform(0.8, 1.2)

            # Расчет цены: преобразуем area в float для расчета, потом обратно в Decimal
            area_float = float(area)
            price_float = round(base_price * price_multiplier * (area_float / 40.0), -2)
            price = Decimal(str(price_float))

            # Создаем предложение
            offer = MarketOffer.objects.create(
                city=city,
                source=random.choice(sources),
                address=address,
                area=area,
                rooms=rooms,
                floor=random.randint(1, 25),
                price=price,
                url=f"https://avito.ru/ekaterinburg/{i}",
                is_active=True,
                parsed_date=datetime.now() - timedelta(days=random.randint(0, 30)),
            )

            self.stdout.write(f"  {address[:35]}... - {area} м², {rooms}к - {price} руб.")

        # Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Тест',
                'last_name': 'Пользователь'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"\nСоздан тестовый пользователь: {user.username}")
        else:
            self.stdout.write(f"\nНайден тестовый пользователь: {user.username}")

        # Создаем квартиры для пользователя
        self.stdout.write("\nСоздание квартир пользователя...")

        user_apartments = [
            ("ул. Ленина, 50", "Екатеринбург", Decimal('45.5'), 2, Decimal('30000')),
            ("ул. Малышева, 31", "Екатеринбург", Decimal('65.0'), 3, Decimal('45000')),
        ]

        for address, city_name, area, rooms, desired_price in user_apartments:
            city = cities[city_name]
            apartment = Apartment.objects.create(
                user=user,
                city=city,
                address=address,
                area=area,
                rooms=rooms,
                floor=random.randint(1, 9),
                total_floors=random.randint(5, 16),
                has_balcony=random.choice([True, False]),
                repair_type=random.choice(['косметический', 'евро']),
                desired_price=desired_price,
            )
            self.stdout.write(f"  {address} - {area} м², {rooms}к - {desired_price} руб.")

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ ДАННЫЕ СОЗДАНЫ УСПЕШНО!"))
        self.stdout.write(f"Городов: {len(cities)}")
        self.stdout.write(f"Предложений: {MarketOffer.objects.count()}")
        self.stdout.write(f"Квартир: {Apartment.objects.count()}")
        self.stdout.write(f"\nТестовый пользователь: {user.username}")
        self.stdout.write(f"Пароль: testpass123")
        self.stdout.write(f"\nДля обновления координат запустите:")
        self.stdout.write(f"python manage.py update_coords_simple")