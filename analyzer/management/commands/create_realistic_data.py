# analyzer/management/commands/create_realistic_data_fixed.py
from django.core.management.base import BaseCommand
from analyzer.models import City, MarketOffer, Apartment
from django.contrib.auth.models import User
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Создание реалистичных тестовых данных (исправленная версия)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие данные'
        )

    def handle(self, *args, **options):
        # Очищаем если нужно
        if options['clear']:
            self.stdout.write("Очистка старых данных...")
            MarketOffer.objects.all().delete()
            Apartment.objects.all().delete()
            City.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✅ Данные очищены"))

        # Создаем города с реальными координатами
        cities_data = [
            {
                'name': 'Екатеринбург',
                'slug': 'ekaterinburg',  # ВРУЧНУЮ задаем slug
                'latitude': 56.8389,
                'longitude': 60.6057,
                'avg_price_per_sqm': Decimal('85000.00'),
                'population': 1500000,
            },
            {
                'name': 'Москва',
                'slug': 'moscow',
                'latitude': 55.7558,
                'longitude': 37.6173,
                'avg_price_per_sqm': Decimal('250000.00'),
                'population': 12000000,
            },
            {
                'name': 'Санкт-Петербург',
                'slug': 'sankt-peterburg',
                'latitude': 59.9343,
                'longitude': 30.3351,
                'avg_price_per_sqm': Decimal('150000.00'),
                'population': 5000000,
            },
            {
                'name': 'Новосибирск',
                'slug': 'novosibirsk',
                'latitude': 55.0084,
                'longitude': 82.9357,
                'avg_price_per_sqm': Decimal('80000.00'),
                'population': 1600000,
            },
        ]

        cities = {}
        for city_data in cities_data:
            try:
                city = City.objects.create(
                    name=city_data['name'],
                    slug=city_data['slug'],  # Обязательно передаем slug
                    latitude=city_data['latitude'],
                    longitude=city_data['longitude'],
                    avg_price_per_sqm=city_data['avg_price_per_sqm'],
                    population=city_data['population'],
                    description=f"Город {city_data['name']}"
                )
                cities[city.name] = city
                self.stdout.write(f"Создан город: {city.name} (slug: {city.slug})")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка создания города {city_data['name']}: {e}"))
                # Пробуем обновить существующий
                try:
                    city = City.objects.get(name=city_data['name'])
                    city.latitude = city_data['latitude']
                    city.longitude = city_data['longitude']
                    city.avg_price_per_sqm = city_data['avg_price_per_sqm']
                    city.population = city_data['population']
                    city.save()
                    cities[city.name] = city
                    self.stdout.write(f"Обновлен город: {city.name}")
                except City.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Не удалось создать город {city_data['name']}"))
                    continue

        # Если не создано ни одного города, выходим
        if not cities:
            self.stdout.write(self.style.ERROR("Не удалось создать ни одного города!"))
            return

        # РЕАЛЬНЫЕ АДРЕСА ЕКАТЕРИНБУРГА
        ekb_addresses = [
            ("ул. Ленина, 50", "Центр"),
            ("ул. Малышева, 31", "Центр"),
            ("пр. Ленина, 24а", "Центр"),
            ("ул. 8 Марта, 8", "Центр"),
            ("ул. Луначарского, 81", "Центр"),
            ("ул. Вильгельма де Геннина, 49", "Академический"),
            ("ул. Краснолесья, 123", "Академический"),
            ("ул. Фрезеровщиков, 54", "Юго-Западный"),
            ("ул. Шейнкмана, 121", "Юго-Западный"),
            ("ул. Белореченская, 24", "Верх-Исетский"),
            ("ул. Кирова, 55", "Верх-Исетский"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА МОСКВЫ
        msk_addresses = [
            ("ул. Тверская, 13", "ЦАО"),
            ("ул. Арбат, 35", "ЦАО"),
            ("ул. Новый Арбат, 15", "ЦАО"),
            ("пр. Вернадского, 125", "ЗАО"),
            ("ул. Ленинский проспект, 89", "ЮЗАО"),
            ("ул. Профсоюзная, 98", "ЮЗАО"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА СПБ
        spb_addresses = [
            ("Невский пр., 28", "Центр"),
            ("ул. Большая Морская, 35", "Центр"),
            ("Литейный пр., 55", "Центр"),
            ("пр. Энгельса, 154", "Выборгский"),
            ("ул. Комсомола, 41", "Выборгский"),
            ("пр. Науки, 65", "Калининский"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА НОВОСИБИРСКА
        nsk_addresses = [
            ("ул. Ленина, 21", "Центр"),
            ("Красный пр., 220", "Центр"),
            ("ул. Советская, 52", "Центр"),
            ("ул. Богдана Хмельницкого, 100", "Заельцовский"),
            ("ул. Кропоткина, 271", "Заельцовский"),
            ("ул. Титова, 205", "Первомайский"),
        ]

        # Создаем рыночные предложения
        self.stdout.write("\nСоздание рыночных предложений...")

        city_addresses = {
            'Екатеринбург': ekb_addresses,
            'Москва': msk_addresses,
            'Санкт-Петербург': spb_addresses,
            'Новосибирск': nsk_addresses,
        }

        sources = ['avito', 'cian', 'yandex']

        for city_name, addresses in city_addresses.items():
            if city_name not in cities:
                continue

            city = cities[city_name]
            self.stdout.write(f"\nГород: {city_name}")

            for i, (address, district) in enumerate(addresses[:8]):  # По 8 на город
                # Генерируем реалистичные параметры
                rooms = random.choice([1, 2, 3])
                area = Decimal(str(round(random.uniform(30, 90), 1)))

                # Цена в зависимости от города и района
                base_price = {
                    'Екатеринбург': 20000,
                    'Москва': 60000,
                    'Санкт-Петербург': 35000,
                    'Новосибирск': 18000,
                }[city_name]

                # Корректировка по району
                if district in ['Центр', 'ЦАО']:
                    price_multiplier = random.uniform(1.3, 1.8)
                else:
                    price_multiplier = random.uniform(0.8, 1.2)

                price = Decimal(str(round(base_price * price_multiplier * (area / 40), -2)))

                # Создаем предложение
                try:
                    offer = MarketOffer.objects.create(
                        city=city,
                        source=random.choice(sources),
                        address=address,
                        area=area,
                        rooms=rooms,
                        floor=random.randint(1, 25),
                        price=price,
                        url=f"https://example.com/{city.slug}/{i}",
                        is_active=True,
                        parsed_date=datetime.now() - timedelta(days=random.randint(0, 30)),
                    )

                    self.stdout.write(f"  {address[:30]}... - {area} м², {rooms}к - {price} руб.")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Ошибка создания предложения: {e}"))

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

        # Создаем несколько квартир для пользователя
        self.stdout.write("\nСоздание квартир пользователя...")

        user_apartments = [
            ("ул. Ленина, 50", "Екатеринбург", Decimal('45.5'), 2, Decimal('30000')),
            ("ул. Малышева, 31", "Екатеринбург", Decimal('65.0'), 3, Decimal('45000')),
            ("Невский пр., 28", "Санкт-Петербург", Decimal('38.0'), 1, Decimal('32000')),
        ]

        for address, city_name, area, rooms, desired_price in user_apartments:
            if city_name not in cities:
                continue

            city = cities[city_name]
            try:
                apartment = Apartment.objects.create(
                    user=user,
                    city=city,
                    address=address,
                    area=area,
                    rooms=rooms,
                    floor=random.randint(1, 9),
                    total_floors=random.randint(5, 16),
                    has_balcony=random.choice([True, False]),
                    repair_type=random.choice(['косметический', 'евро', 'дизайнерский']),
                    desired_price=desired_price,
                )
                self.stdout.write(f"  {address[:30]}... - {area} м², {rooms}к - {desired_price} руб.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Ошибка создания квартиры: {e}"))

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ РЕАЛИСТИЧНЫЕ ДАННЫЕ СОЗДАНЫ!"))
        self.stdout.write(f"Всего городов: {len(cities)}")
        self.stdout.write(f"Всего предложений: {MarketOffer.objects.count()}")
        self.stdout.write(f"Всего квартир: {Apartment.objects.count()}")
        self.stdout.write(f"\nТестовый пользователь: {user.username}")
        self.stdout.write(f"Пароль: testpass123")