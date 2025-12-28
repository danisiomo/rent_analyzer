# test_geocoder_simple.py
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.geocoder_simple import simple_geocoder


def test_geocoder():
    """Тестирование геокодирования"""

    # Тестовые адреса - реальные существующие
    test_cases = [
        # Простые существующие адреса
        ("улица Садовая 4", "Екатеринбург"),
        ("улица Ленина 85", "Екатеринбург"),
        ("улица Кирова 116", "Екатеринбург"),

        # Адреса из вашей базы данных (формат как у вас)
        ("ул. Садовая, 4", "Екатеринбург"),
        ("ул. Ленина, 85", "Екатеринбург"),
        ("ул. Кирова, 116", "Екатеринбург"),
        ("ул. Пушкина, 148", "Санкт-Петербург"),
        ("ул. Советская, 45", "Санкт-Петербург"),

        # Адреса с районом
        ("Санкт-Петербург, Василеостровский, ул. Пушкина, 148", None),
        ("Санкт-Петербург, Красногвардейский, ул. Кирова, 66", None),

        # Адреса без номера (только улица)
        ("улица Садовая", "Екатеринбург"),
        ("проспект Ленина", "Екатеринбург"),
    ]

    print("=" * 80)
    print("ТЕСТ ГЕОКОДИРОВАНИЯ ЧЕРЕЗ NOMINATIM")
    print("=" * 80)

    for i, (address, city) in enumerate(test_cases, 1):
        print(f"\n{i}. Адрес: {address}")
        if city:
            print(f"   Город: {city}")

        # Тест 1: Простой поиск
        print("   Простой поиск...")
        result_simple = simple_geocoder.geocode_simple(address, city)

        if result_simple:
            print(f"   ✓ Найдено: {result_simple['lat']:.6f}, {result_simple['lon']:.6f}")
            display = result_simple.get('display_name', '')
            if len(display) > 120:
                display = display[:120] + "..."
            print(f"   Адрес: {display}")
        else:
            print("   ✗ Не найдено (простой поиск)")

        # Пауза между запросами
        if i < len(test_cases):
            time.sleep(1.5)

        # Тест 2: Структурированный поиск (если есть улица и номер)
        if any(word in address.lower() for word in ['ул.', 'улица', 'пр.', 'проспект']):
            print("   Структурированный поиск...")
            result_structured = simple_geocoder.geocode_structured(address, city)

            if result_structured:
                print(f"   ✓ Найдено: {result_structured['lat']:.6f}, {result_structured['lon']:.6f}")
                params = result_structured.get('params_used', {})
                if 'street' in params:
                    print(f"   Параметры: street={params.get('street')}")
            else:
                print("   ✗ Не найдено (структурированный)")

            # Пауза
            if i < len(test_cases):
                time.sleep(1.5)


if __name__ == "__main__":
    import time

    test_geocoder()