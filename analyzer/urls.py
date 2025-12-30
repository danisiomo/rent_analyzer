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
    path('apartment/<int:pk>/', views.apartment_detail, name='apartment_detail'),
    path('apartment/<int:pk>/delete/', views.delete_apartment, name='delete_apartment'),
    path('apartment/<int:apartment_id>/analyze/', views.analyze_apartment, name='analyze_apartment'),
    path('apartment/<int:apartment_id>/results/', views.analysis_results, name='analysis_results'),
    path('apartment/<int:apartment_id>/save-report/', views.save_analysis_report, name='save_analysis_report'),

    # Тесты
    path('test-charts/', views.test_charts, name='test_charts'),
    path('report/<int:pk>/', views.analysis_detail, name='analysis_detail'),

    # Альтернативный маршрут для отчетов
    path('analysis/report/<int:report_id>/', views.view_report_detail, name='view_report_detail'),
    path('analysis/<int:pk>/delete/', views.delete_report, name='delete_report'),
    #path('analysis/compare/', views.compare_reports, name='compare_reports'),
    path('market-offers/', views.MarketOffersListView.as_view(), name='market_offers'),
    # Список городов
    path('cities/', views.CityListView.as_view(), name='city_list'),

    # Рыночные предложения
    path('offers/', views.MarketOffersListView.as_view(), name='market_offers'),
]