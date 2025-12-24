from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    # Главная страница приложения analyzer
    path('', views.home, name='home'),

    # Личный кабинет пользователя
    path('dashboard/', views.dashboard, name='dashboard'),

    # Форма для анализа
    path('analyze/', views.analyze_form, name='analyze'),

    # Список городов
    path('cities/', views.CityListView.as_view(), name='city_list'),

    # Рыночные предложения
    path('offers/', views.MarketOffersListView.as_view(), name='market_offers'),
]