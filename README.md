RentAnalyzer

Веб-сервис для анализа рынка аренды жилья с расчетом справедливой стоимости на основе сравнительного анализа рыночных данных

Предварительные требования
- Python 3.10+
- Django 4.2+
- Git

Установка
```bash
# Клонирование репозитория:
git clone https://github.com/username/rent_analyzer.git
cd rent_analyzer

Создание виртуального окружения:
python -m venv venv
venv\Scripts\activate  # Windows
  # source venv/bin/activate  # Linux/Mac

Установка зависимостей:
pip install -r requirements.txt

Применение миграций:
python manage.py migrate

Создание суперпользователя:
python manage.py createsuperuser

Запуск сервера:
python manage.py runserver
