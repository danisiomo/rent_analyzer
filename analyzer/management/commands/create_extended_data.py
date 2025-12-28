
from django.core.management.base import BaseCommand
from analyzer.models import City, MarketOffer, Apartment
from django.contrib.auth.models import User
import random
from decimal import Decimal
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Создание расширенной базы с реальными адресами Москвы, СПб и Екатеринбурга'

    def handle(self, *args, **options):
        self.stdout.write("Создание расширенной базы данных...")

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

        # Новосибирск (дополнительно)
        city, created = City.objects.get_or_create(
            name='Новосибирск',
            defaults={
                'latitude': 55.0084,
                'longitude': 82.9357,
                'avg_price_per_sqm': Decimal('80000.00'),
                'population': 1600000,
            }
        )
        cities['Новосибирск'] = city
        self.stdout.write(f"{'Создан' if created else 'Найден'} город: {city.name}")

        # Удаляем старые предложения
        MarketOffer.objects.all().delete()
        self.stdout.write("Старые предложения удалены")

        # РЕАЛЬНЫЕ АДРЕСА ЕКАТЕРИНБУРГА (30 шт)
        ekb_addresses = [
            # Центр
            ("ул. Ленина, 50", "центр"),
            ("ул. Малышева, 31", "центр"),
            ("пр. Ленина, 24а", "центр"),
            ("ул. 8 Марта, 8", "центр"),
            ("ул. Луначарского, 81", "центр"),
            ("ул. Горького, 27", "центр"),
            ("ул. Хохрякова, 85", "центр"),
            ("ул. Московская, 19", "центр"),

            # Академический
            ("ул. Вильгельма де Геннина, 49", "академический"),
            ("ул. Краснолесья, 123", "академический"),
            ("ул. Академика Сахарова, 107", "академический"),
            ("ул. Павла Шаманова, 22", "академический"),

            # Юго-Западный
            ("ул. Фрезеровщиков, 54", "юго-западный"),
            ("ул. Шейнкмана, 121", "юго-западный"),
            ("ул. Бардина, 28", "юго-западный"),
            ("ул. Сулимова, 50", "юго-западный"),

            # Верх-Исетский
            ("ул. Белореченская, 24", "верх-исетский"),
            ("ул. Кирова, 55", "верх-исетский"),
            ("ул. Татищева, 88", "верх-исетский"),
            ("ул. Репина, 94", "верх-исетский"),

            # ЖБИ
            ("ул. Комсомольская, 67", "жби"),
            ("ул. Рассветная, 12", "жби"),
            ("ул. Сыромолотова, 16", "жби"),
            ("ул. Юлиуса Фучика, 3", "жби"),

            # Уралмаш
            ("ул. Машиностроителей, 19", "уралмаш"),
            ("ул. Культуры, 3", "уралмаш"),
            ("ул. Старых Большевиков, 52", "уралмаш"),
            ("ул. 22 Партсъезда, 15", "уралмаш"),

            # Вокзальный
            ("ул. Челюскинцев, 106", "вокзальный"),
            ("ул. Первомайская, 104", "вокзальный"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА МОСКВЫ (30 шт)
        msk_addresses = [
            # ЦАО (центр)
            ("ул. Тверская, 13", "цао"),
            ("ул. Арбат, 35", "цао"),
            ("ул. Новый Арбат, 15", "цао"),
            ("ул. Большая Дмитровка, 15", "цао"),
            ("ул. Петровка, 25", "цао"),
            ("ул. Мясницкая, 20", "цао"),
            ("ул. Покровка, 27", "цао"),

            # САО
            ("Ленинградский пр., 37", "сао"),
            ("ул. Верхняя Масловка, 18", "сао"),
            ("ул. Врубеля, 6", "сао"),
            ("ул. Панфилова, 4", "сао"),

            # СВАО
            ("пр. Мира, 186", "свао"),
            ("ул. Ярославская, 8", "свао"),
            ("ул. Менжинского, 32", "свао"),
            ("ул. Коминтерна, 18", "свао"),

            # ВАО
            ("ш. Энтузиастов, 12", "вао"),
            ("ул. Первомайская, 89", "вао"),
            ("ул. 9-я Парковая, 48", "вао"),
            ("ул. Вешняковская, 20", "вао"),

            # ЮВАО
            ("ул. Верхние Поля, 45", "ювао"),
            ("ул. Маршала Чуйкова, 26", "ювао"),
            ("Волгоградский пр., 42", "ювао"),

            # ЮАО
            ("ул. Кантемировская, 59", "юао"),
            ("ул. Домодедовская, 20", "юао"),
            ("ул. Красного Маяка, 15", "юао"),

            # ЮЗАО
            ("ул. Профсоюзная, 98", "юзао"),
            ("ул. Миклухо-Маклая, 57", "юзао"),
            ("Ленинский пр., 89", "юзао"),
            ("ул. Обручева, 38", "юзао"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА САНКТ-ПЕТЕРБУРГА (30 шт)
        spb_addresses = [
            # Центр
            ("Невский пр., 28", "центр"),
            ("ул. Большая Морская, 35", "центр"),
            ("Литейный пр., 55", "центр"),
            ("ул. Садовая, 54", "центр"),
            ("наб. реки Фонтанки, 92", "центр"),
            ("ул. Рубинштейна, 36", "центр"),
            ("ул. Марата, 72", "центр"),

            # Василеостровский
            ("ул. Кораблестроителей, 30", "василеостровский"),
            ("пр. КИМа, 28", "василеостровский"),
            ("ул. Нахимова, 10", "василеостровский"),
            ("ул. Гаванская, 50", "василеостровский"),

            # Петроградский
            ("ул. Льва Толстого, 9", "петроградский"),
            ("ул. Профессора Попова, 37", "петроградский"),
            ("Каменноостровский пр., 42", "петроградский"),

            # Выборгский
            ("пр. Энгельса, 154", "выборгский"),
            ("ул. Комсомола, 41", "выборгский"),
            ("пр. Пархоменко, 20", "выборгский"),
            ("ул. Жака Дюкло, 21", "выборгский"),

            # Калининский
            ("пр. Науки, 65", "калининский"),
            ("ул. Руставели, 66", "калининский"),
            ("Гражданский пр., 111", "калининский"),
            ("ул. Демьяна Бедного, 22", "калининский"),

            # Кировский
            ("пр. Стачек, 48", "кировский"),
            ("ул. Маршала Казакова, 35", "кировский"),
            ("ул. Зенитчиков, 10", "кировский"),
            ("пр. Ветеранов, 89", "кировский"),

            # Московский
            ("Московский пр., 216", "московский"),
            ("ул. Типанова, 28", "московский"),
            ("ул. Пулковская, 10", "московский"),

            # Фрунзенский
            ("ул. Белы Куна, 3", "фрунзенский"),
            ("ул. Софийская, 44", "фрунзенский"),
        ]

        # РЕАЛЬНЫЕ АДРЕСА НОВОСИБИРСКА (20 шт)
        nsk_addresses = [
            ("ул. Ленина, 21", "центр"),
            ("Красный пр., 220", "центр"),
            ("ул. Советская, 52", "центр"),
            ("ул. Каинская, 68", "центр"),
            ("ул. Горького, 78", "центр"),
            ("ул. Богдана Хмельницкого, 100", "заельцовский"),
            ("ул. Кропоткина, 271", "заельцовский"),
            ("ул. Титова, 205", "первомайский"),
            ("ул. Героев Революции, 64", "октябрьский"),
            ("ул. Кирова, 82", "октябрьский"),
            ("ул. Никитина, 20", "советский"),
            ("ул. Ильича, 6", "советский"),
            ("ул. Выборная, 126", "кировский"),
            ("ул. Сибиряков-Гвардейцев, 47", "кировский"),
            ("ул. Станционная, 30", "ленинский"),
            ("ул. Тюленина, 15", "ленинский"),
        ]

        # Создаем рыночные предложения
        self.stdout.write("\nСоздание рыночных предложений...")

        city_data = {
            'Екатеринбург': (ekb_addresses, 20000),
            'Москва': (msk_addresses, 60000),
            'Санкт-Петербург': (spb_addresses, 35000),
            'Новосибирск': (nsk_addresses, 18000),
        }

        sources = ['avito', 'cian', 'yandex']

        for city_name, (addresses, base_price) in city_data.items():
            if city_name not in cities:
                continue

            city = cities[city_name]
            self.stdout.write(f"\nГород: {city_name} ({len(addresses)} адресов)")

            for i, (address, district) in enumerate(addresses):
                # Генерируем параметры
                rooms = random.choice([1, 2, 3, 4])
                area = Decimal(str(round(random.uniform(30.0, 120.0), 1)))

                # Корректировка по району
                if district in ['центр', 'цао']:
                    price_multiplier = random.uniform(1.4, 2.0)
                elif district in ['академический', 'сао', 'василеостровский']:
                    price_multiplier = random.uniform(1.1, 1.5)
                else:
                    price_multiplier = random.uniform(0.7, 1.2)

                # Расчет цены
                area_float = float(area)
                price_float = round(base_price * price_multiplier * (area_float / 40.0), -2)
                price = Decimal(str(price_float))

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
                        url=f"https://{random.choice(sources)}.ru/{city_name.lower()}/{i}",
                        is_active=True,
                        parsed_date=datetime.now() - timedelta(days=random.randint(0, 60)),
                    )

                    self.stdout.write(f"  ✓ {address[:35]}... - {area} м², {rooms}к - {price:,.0f} руб.")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Ошибка: {address} - {e}"))

        # Создаем/обновляем тестового пользователя
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

        # Создаем квартиры для пользователя в разных городах
        self.stdout.write("\nСоздание квартир пользователя в разных городах...")

        Apartment.objects.filter(user=user).delete()

        user_apartments = [
            ("ул. Ленина, 50", "Екатеринбург", Decimal('45.5'), 2, Decimal('32000')),
            ("ул. Малышева, 31", "Екатеринбург", Decimal('68.0'), 3, Decimal('48000')),
            ("Невский пр., 28", "Санкт-Петербург", Decimal('38.5'), 1, Decimal('35000')),
            ("ул. Тверская, 13", "Москва", Decimal('55.0'), 2, Decimal('85000')),
            ("Красный пр., 220", "Новосибирск", Decimal('42.0'), 1, Decimal('22000')),
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
                    floor=random.randint(1, 12),
                    total_floors=random.randint(5, 25),
                    has_balcony=random.choice([True, False]),
                    repair_type=random.choice(['косметический', 'евро', 'дизайнерский']),
                    description=f"Квартира в районе {address.split(',')[-2] if ',' in address else 'центре'}",
                    desired_price=desired_price,
                )
                self.stdout.write(f"  ✓ {city_name}: {address} - {area} м², {rooms}к")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Ошибка создания квартиры: {e}"))

        # Статистика
        total_offers = MarketOffer.objects.count()
        total_apartments = Apartment.objects.count()

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ РАСШИРЕННАЯ БАЗА ДАННЫХ СОЗДАНА!"))
        self.stdout.write("=" * 70)

        # Статистика по городам
        self.stdout.write("\nСТАТИСТИКА:")
        for city_name in cities.keys():
            offers_count = MarketOffer.objects.filter(city__name=city_name).count()
            apartments_count = Apartment.objects.filter(city__name=city_name).count()
            self.stdout.write(f"  {city_name}: {offers_count} предложений, {apartments_count} квартир")

        self.stdout.write(f"\nВСЕГО: {total_offers} рыночных предложений")
        self.stdout.write(f"      {total_apartments} квартир пользователей")
        self.stdout.write(f"\nТестовый пользователь: {user.username} (пароль: testpass123)")
        self.stdout.write(f"\nДЛЯ ОБНОВЛЕНИЯ КООРДИНАТ:")
        self.stdout.write(f"python manage.py update_all_coords --delay 2.0")