from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from .models import Apartment, City, MarketOffer, AnalysisReport


def home(request):
    """Главная страница приложения"""
    # Статистика для главной страницы
    cities = City.objects.all()[:5]  # 5 первых городов
    total_apartments = Apartment.objects.count()
    total_offers = MarketOffer.objects.filter(is_active=True).count()

    context = {
        'cities': cities,
        'total_apartments': total_apartments,
        'total_offers': total_offers,
    }
    return render(request, 'analyzer/home.html', context)


@login_required
def dashboard(request):
    """Личный кабинет пользователя"""
    # Квартиры текущего пользователя
    user_apartments = Apartment.objects.filter(user=request.user)
    # Отчеты анализа для квартир пользователя
    reports = AnalysisReport.objects.filter(apartment__user=request.user)

    context = {
        'user_apartments': user_apartments,
        'reports': reports,
    }
    return render(request, 'analyzer/dashboard.html', context)


@login_required
def analyze_form(request):
    """Форма для анализа новой квартиры"""
    cities = City.objects.all()
    context = {
        'cities': cities,
    }
    return render(request, 'analyzer/analyze_form.html', context)


class CityListView(ListView):
    """Список городов"""
    model = City
    template_name = 'analyzer/city_list.html'
    context_object_name = 'cities'
    paginate_by = 10


class MarketOffersListView(ListView):
    """Список рыночных предложений"""
    model = MarketOffer
    template_name = 'analyzer/market_offers.html'
    context_object_name = 'offers'
    paginate_by = 20

    def get_queryset(self):
        queryset = MarketOffer.objects.filter(is_active=True)
        # Фильтрация по городу
        city_id = self.request.GET.get('city')
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        return queryset.order_by('-parsed_date')