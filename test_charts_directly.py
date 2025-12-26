#!/usr/bin/env python
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from analyzer.models import Apartment, MarketOffer
from utils.charts import chart_generator

# Получаем данные
apartment = Apartment.objects.get(id=4)
offers = list(MarketOffer.objects.filter(
    city=apartment.city,
    rooms=apartment.rooms,
    is_active=True
)[:10])

print(f"Квартира: {apartment.address}")
print(f"Предложений: {len(offers)}")
print(f"Первые 3 предложения:")
for i, offer in enumerate(offers[:3]):
    print(f"  {i + 1}. {offer.price} руб., {offer.area} м²")

if len(offers) >= 3:
    print("\nТестируем chart_generator...")

    # Тест 1: Простая гистограмма
    print("\n1. Тест гистограммы:")
    try:
        chart = chart_generator.create_price_distribution_chart(
            offers,
            apartment_price=float(apartment.desired_price)
        )
        if chart:
            print(f"   ✓ Успешно! Длина: {len(chart)} символов")
            # Проверяем первые 100 символов
            print(f"   Начало: {chart[:100]}...")
        else:
            print("   ✗ Вернул пустую строку")
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    # Тест 2: Scatter plot
    print("\n2. Тест scatter plot:")
    try:
        chart = chart_generator.create_price_vs_area_scatter(
            offers,
            apartment_area=float(apartment.area),
            apartment_price=float(apartment.desired_price)
        )
        if chart:
            print(f"   ✓ Успешно! Длина: {len(chart)} символов")
        else:
            print("   ✗ Вернул пустую строку")
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")

    # Тест 3: Создание файла напрямую
    print("\n3. Тест создания файла напрямую через matplotlib:")
    try:
        import matplotlib

        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        prices = [float(o.price) for o in offers]
        areas = [float(o.area) for o in offers]

        plt.figure(figsize=(10, 6))
        plt.scatter(areas, prices)
        plt.xlabel('Площадь, м²')
        plt.ylabel('Цена, руб.')
        plt.title('Прямой тест matplotlib')
        plt.savefig('direct_test.png')
        plt.close()

        print("   ✓ Файл создан: direct_test.png")

    except Exception as e:
        print(f"   ✗ Ошибка: {e}")