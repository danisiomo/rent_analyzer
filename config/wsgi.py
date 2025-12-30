import os
import sys

# Путь к проекту
path = '/home/danisiomo/rent_analyzer'
if path not in sys.path:
    sys.path.append(path)

# Активируем виртуальное окружение
activate_this = '/home/danisiomo/rent_analyzer/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Запуск приложения
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()