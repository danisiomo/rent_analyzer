# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # Импортируем представления, которые создадим позже

app_name = 'users'

urlpatterns = [
    # Временные маршруты для аутентификации (используем встроенные представления)
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    # Маршрут для регистрации (создадим позже)
    # path('register/', views.register, name='register'),
]