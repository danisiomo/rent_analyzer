# analyzer/management/commands/add_more_apartments.py
from django.core.management.base import BaseCommand
from analyzer.models import City, Apartment
from django.contrib.auth.models import User
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Добавление дополнительных квартир для тестирования'

    def handle(self, *args, **options):
        self.stdout.write("Добавление дополнительных квартир для тестирования...")

        # Получаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )

        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"Создан пользователь: {user.username}")
        else:
            self.stdout.write(f"Найден пользователь: {user.username}")

        # Дополнительные квартиры
        new_apartments = [
            # Екатеринбург
            ("ул. Розы Люксембург, 49", "Екатеринбург", Decimal('52.0'), 2, Decimal('38000')),
            ("ул. Куйбышева, 55", "Екатеринбург", Decimal('68.5'), 3, Decimal('52000')),
            ("ул. Токарей, 34", "Екатеринбург", Decimal('42.5'), 1, Decimal('28000')),
            ("ул. Большакова, 90", "Екатеринбург", Decimal('75.0'), 3, Decimal('48000')),

            # Москва
            ("ул. Крылатские Холмы, 30", "Москва", Decimal('65.0'), 2, Decimal('120000')),
            ("ул. Осенняя, 16", "Москва", Decimal('48.5'), 1, Decimal('85000')),
            ("ул. Ярцевская, 28", "Москва", Decimal('85.0'), 3, Decimal('145000')),
            ("ул. Флотская, 66", "Москва", Decimal('72.5'), 2, Decimal('110000')),

            # Санкт-Петербург
            ("ул. Гороховая, 46", "Санкт-Петербург", Decimal('45.0'), 1, Decimal('42000')),
            ("ул. Некрасова, 58", "Санкт-Петербург", Decimal('62.0'), 2, Decimal('58000')),
            ("пр. Косыгина, 28", "Санкт-Петербург", Decimal('38.5'), 1, Decimal('32000')),
            ("ул. Савушкина, 128", "Санкт-Петербург", Decimal('55.0'), 2, Decimal('52000')),

            # Новосибирск
            ("ул. Сибиряков-Гвардейцев, 47", "Новосибирск", Decimal('44.0'), 1, Decimal('24000')),
            ("ул. Тюленина, 15", "Новосибирск", Decimal('58.0'), 2, Decimal('32000')),
        ]

        added_count = 0

        for address, city_name, area, rooms, desired_price in new_apartments:
            try:
                city = City.objects.get(name=city_name)

                # Проверяем, нет ли уже такой квартиры
                if Apartment.objects.filter(user=user, city=city, address=address).exists():
                    self.stdout.write(f"  ⚠ Уже существует: {address}")
                    continue

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
                    description=f"Тестовая квартира для анализа в районе {address.split(',')[0]}",
                    desired_price=desired_price,
                )

                added_count += 1
                self.stdout.write(f"  ✓ {city_name}: {address}")
                self.stdout.write(f"    {area} м², {rooms}к - {desired_price} руб.")

            except City.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  ✗ Город {city_name} не найден"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Ошибка: {e}"))

        # Итог
        total_apartments = Apartment.objects.filter(user=user).count()

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ ДОБАВЛЕНИЕ ЗАВЕРШЕНО!"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"\n📊 СТАТИСТИКА:")
        self.stdout.write(f"   Добавлено новых квартир: {added_count}")
        self.stdout.write(f"   Всего квартир у пользователя: {total_apartments}")
        self.stdout.write(f"\n👤 Пользователь: {user.username}")
        self.stdout.write(f"🔑 Пароль: testpass123")