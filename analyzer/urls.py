from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    # Главная страница приложения analyzer
    path('', views.home, name='home'),

    # Личный кабинет пользователя
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update-data/', views.update_market_data, name='update_market_data'),
    # Квартиры
    path('apartment/add/', views.add_apartment, name='add_apartment'),
    path('apartment/<int:apartment_id>/analyze/', views.analyze_apartment, name='analyze_apartment'),
    path('apartment/<int:apartment_id>/results/', views.analysis_results, name='analysis_results'),
    path('apartment/<int:apartment_id>/save-report/', views.save_analysis_report, name='save_analysis_report'),

    # Список городов
    path('cities/', views.CityListView.as_view(), name='city_list'),

    # Рыночные предложения
    path('offers/', views.MarketOffersListView.as_view(), name='market_offers'),
]