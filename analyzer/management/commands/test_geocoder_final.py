# analyzer/management/commands/test_geocoder_final.py
from django.core.management.base import BaseCommand
import requests
import time
import json


class Command(BaseCommand):
    help = 'Прямой тест геокодирования как в работающем примере'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("ПРЯМОЙ ТЕСТ NOMINATIM (как в работающем примере)")
        self.stdout.write("=" * 80)

        test_cases = [
            ("ул. Садовая, 4", "Екатеринбург"),
            ("ул. Ленина, 85", "Екатеринбург"),
            ("ул. Кирова, 116", "Екатеринбург"),
            ("ул. Пушкина, 148", "Санкт-Петербург"),
            ("ул. Советская, 45", "Санкт-Петербург"),
        ]

        for address, city in test_cases:
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(f"ТЕСТ: {address}, {city}")
            self.stdout.write(f"{'=' * 60}")

            # Способ 1: Как в работающем тесте
            self.stdout.write("\nСпособ 1: Прямой запрос")

            # Форматируем адрес
            formatted_address = f"{address.replace('ул.', 'улица').replace('пр.', 'проспект')}, {city}, Россия"
            # Убираем запятую между улицей и номером
            formatted_address = formatted_address.replace(', ', ' ', 1).replace(',', '', 1)

            self.stdout.write(f"Запрос: {formatted_address}")

            try:
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        'q': formatted_address,
                        'format': 'json',
                        'limit': 1,
                        'countrycodes': 'ru',
                    },
                    headers={'User-Agent': 'RentAnalyzerPro/1.0'},
                    timeout=10
                )

                self.stdout.write(f"Статус: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if data:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Найдено: {data[0]['lat']}, {data[0]['lon']}"
                            )
                        )
                        self.stdout.write(f"Адрес: {data[0]['display_name'][:100]}...")
                    else:
                        self.stdout.write(self.style.WARNING("✗ Не найдено"))
                else:
                    self.stdout.write(self.style.ERROR(f"Ошибка: {response.status_code}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Исключение: {e}"))

            # Пауза
            time.sleep(1.5)

            # Способ 2: Структурированный
            self.stdout.write("\nСпособ 2: Структурированный запрос")

            try:
                # Парсим адрес
                street_part = address.split(',')[0].strip()
                street_part = street_part.replace('ул.', 'улица').replace('пр.', 'проспект')

                response2 = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        'street': street_part,
                        'city': city,
                        'country': 'Россия',
                        'format': 'json',
                        'limit': 1,
                    },
                    headers={'User-Agent': 'RentAnalyzerPro/1.0'},
                    timeout=10
                )

                self.stdout.write(f"Статус: {response2.status_code}")

                if response2.status_code == 200:
                    data = response2.json()
                    if data:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Найдено: {data[0]['lat']}, {data[0]['lon']}"
                            )
                        )
                    else:
                        self.stdout.write(self.style.WARNING("✗ Не найдено"))
                else:
                    self.stdout.write(self.style.ERROR(f"Ошибка: {response2.status_code}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Исключение: {e}"))

            # Пауза между тестами
            if test_cases.index((address, city)) < len(test_cases) - 1:
                time.sleep(1.5)