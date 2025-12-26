from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Count, Avg, Min, Max
from .models import Apartment, City, MarketOffer, AnalysisReport
from .forms import ApartmentForm, AnalysisFilterForm
from utils.analyzer import ApartmentAnalyzer
from utils.geocoder import geocoder
from utils.charts import chart_generator
import logging



try:
    from utils.charts import chart_generator
    CHARTS_AVAILABLE = True
except ImportError as e:
    chart_generator = None
    CHARTS_AVAILABLE = False
    logging.warning(f"Chart generator not available: {e}")

logger = logging.getLogger(__name__)

# Главная страница приложения analyzer
def home(request):
    """Главная страница приложения analyzer"""
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
def add_apartment(request):
    """Добавление новой квартиры"""
    if request.method == 'POST':
        form = ApartmentForm(request.POST)
        if form.is_valid():
            apartment = form.save(commit=False)
            apartment.user = request.user

            # Пробуем геокодировать адрес
            try:
                result = geocoder.geocode(
                    apartment.address,
                    apartment.city.name if apartment.city else None
                )
                if result:
                    apartment.latitude = result['lat']
                    apartment.longitude = result['lon']
                    messages.success(request, 'Адрес успешно геокодирован!')
            except Exception as e:
                messages.warning(request, f'Геокодирование не удалось: {str(e)}')

            apartment.save()
            messages.success(request, 'Квартира успешно добавлена!')

            # Предлагаем сразу проанализировать
            return redirect('analyzer:analyze_apartment', apartment_id=apartment.id)
    else:
        form = ApartmentForm()

    return render(request, 'analyzer/add_apartment.html', {
        'form': form,
        'title': 'Добавить квартиру для анализа'
    })


@login_required
def analyze_apartment(request, apartment_id):
    """Анализ конкретной квартиры"""
    apartment = get_object_or_404(Apartment, id=apartment_id, user=request.user)

    if request.method == 'POST':
        filter_form = AnalysisFilterForm(request.POST)
        if filter_form.is_valid():
            # Получаем параметры анализа и преобразуем в float
            area_tolerance = float(filter_form.cleaned_data['area_tolerance'])
            price_tolerance = float(filter_form.cleaned_data['price_tolerance'])
            include_same_floor = filter_form.cleaned_data['include_same_floor']
            min_similar_offers = int(filter_form.cleaned_data['min_similar_offers'])

            # Запускаем анализ
            analyzer = ApartmentAnalyzer(apartment)
            results = analyzer.analyze(
                area_tolerance=area_tolerance,
                price_tolerance=price_tolerance,
                include_same_floor=include_same_floor,
                max_results=50
            )

            # Проверяем достаточно ли похожих предложений
            if results['count'] < min_similar_offers:
                messages.warning(
                    request,
                    f'Найдено только {results["count"]} похожих предложений '
                    f'(минимум {min_similar_offers}). Попробуйте изменить параметры.'
                )
            else:
                messages.success(request, 'Анализ успешно выполнен!')

            # Конвертируем Decimal в float для сериализации в JSON
            serializable_results = results.copy()

            # Преобразуем Decimal поля в float
            decimal_fields = ['avg_price', 'median_price', 'min_price', 'max_price',
                              'avg_price_per_sqm', 'fair_price', 'price_difference']

            for field in decimal_fields:
                if field in serializable_results and hasattr(serializable_results[field], 'quantize'):
                    serializable_results[field] = float(serializable_results[field])

            # Удаляем несериализуемые объекты
            if 'apartment' in serializable_results:
                del serializable_results['apartment']

            # Сохраняем результаты в сессии для отображения
            request.session['analysis_results'] = {
                'apartment_id': apartment.id,
                'results': serializable_results,
                'similar_offers_count': results['count'],
            }

            return redirect('analyzer:analysis_results', apartment_id=apartment.id)
    else:
        filter_form = AnalysisFilterForm()

    return render(request, 'analyzer/analyze_apartment.html', {
        'apartment': apartment,
        'form': filter_form,
        'title': f'Анализ квартиры: {apartment.address}'
    })


def test_charts(request):
    """Тестовое представление для проверки графиков"""
    from analyzer.models import Apartment, MarketOffer
    from utils.charts import chart_generator

    apartment = Apartment.objects.first()
    offers = list(MarketOffer.objects.filter(is_active=True)[:10])

    charts = {}

    if apartment and len(offers) >= 3:
        # Тестовый график 1
        chart1 = chart_generator.create_price_distribution_chart(
            offers,
            apartment_price=float(apartment.desired_price) if apartment.desired_price else None,
            title="Тестовый график 1"
        )

        # Тестовый график 2
        chart2 = chart_generator.create_price_vs_area_scatter(
            offers,
            apartment_area=float(apartment.area) if apartment.area else None,
            apartment_price=float(apartment.desired_price) if apartment.desired_price else None,
            title="Тестовый график 2"
        )

        if chart1:
            charts['chart1'] = chart1

        if chart2:
            charts['chart2'] = chart2

    return render(request, 'analyzer/test_charts.html', charts)


@login_required
def analysis_results(request, apartment_id):
    """Просмотр результатов анализа с графиками"""
    apartment = get_object_or_404(Apartment, id=apartment_id, user=request.user)

    # Получаем результаты из сессии
    analysis_data = request.session.get('analysis_results', {})

    if not analysis_data or analysis_data.get('apartment_id') != apartment.id:
        messages.info(request, 'Результаты анализа не найдены. Запустите анализ сначала.')
        return redirect('analyzer:analyze_apartment', apartment_id=apartment.id)

    results = analysis_data['results']

    # Форматируем числа для отображения
    formatted_results = {
        **results,
        'avg_price': f"{results['avg_price']:,.0f}".replace(',', ' '),
        'median_price': f"{results['median_price']:,.0f}".replace(',', ' '),
        'min_price': f"{results['min_price']:,.0f}".replace(',', ' '),
        'max_price': f"{results['max_price']:,.0f}".replace(',', ' '),
        'fair_price': f"{results['fair_price']:,.0f}".replace(',', ' '),
        'price_difference': f"{results['price_difference']:.1f}",
        'price_range': f"{results['min_price']:,.0f} - {results['max_price']:,.0f}",
        'recommendation_type': results.get('recommendation_type', 'info'),
        'avg_price_per_sqm': f"{results.get('avg_price_per_sqm', 0):,.0f}",
    }

    # Получаем похожие предложения ЧЕРЕЗ АНАЛИЗАТОР
    analyzer = ApartmentAnalyzer(apartment)

    # Важно: используем те же параметры, что были в анализе
    area_tolerance = float(analysis_data.get('area_tolerance', 20))
    price_tolerance = float(analysis_data.get('price_tolerance', 30))
    include_same_floor = analysis_data.get('include_same_floor', False)

    similar_offers = analyzer.find_similar_offers(
        area_tolerance=area_tolerance,
        price_tolerance=price_tolerance,
        include_same_floor=include_same_floor,
        max_results=50
    )

    # Проверяем, что получили
    logger.info(f"Найдено похожих предложений: {len(similar_offers)}")
    if similar_offers:
        logger.info(f"Пример первого предложения: {similar_offers[0].price} руб., {similar_offers[0].area} м²")

    # Создаем графики (если доступны)
    charts = {}

    # Проверяем, что есть достаточно данных
    has_enough_data = len(similar_offers) >= 3

    if CHARTS_AVAILABLE and chart_generator and has_enough_data:
        try:
            logger.info(f"Создание графиков: {len(similar_offers)} предложений")

            # Подготавливаем статистику для графиков
            market_stats = {
                'avg_price': float(results['avg_price']),
                'median_price': float(results['median_price']),
                'min_price': float(results['min_price']),
                'max_price': float(results['max_price'])
            }

            # Тестируем каждый график отдельно
            test_prices = [float(offer.price) for offer in similar_offers[:5]]
            test_areas = [float(offer.area) for offer in similar_offers[:5]]
            logger.info(f"Тестовые данные: цены={test_prices}, площади={test_areas}")

            # Пробуем создать простой график
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            import base64

            # Тестовый график
            plt.figure(figsize=(8, 6))
            prices = [float(offer.price) for offer in similar_offers]
            plt.hist(prices, bins=10, alpha=0.7)
            plt.xlabel('Цена')
            plt.ylabel('Количество')
            plt.title('Тестовый график')

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            test_chart = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()

            charts['test_chart'] = test_chart
            logger.info("✓ Тестовый график создан")

            # Теперь пытаемся создать графики через chart_generator
            try:
                chart1 = chart_generator.create_price_distribution_chart(
                    similar_offers,
                    apartment_price=float(apartment.desired_price),
                    title=f"Распределение цен в {apartment.city.name}"
                )
                if chart1 and len(chart1) > 100:  # Проверяем, что не пустая строка
                    charts['price_distribution'] = chart1
                    logger.info(f"✓ Гистограмма создана ({len(chart1)} символов)")
                else:
                    logger.warning(
                        f"⚠ Гистограмма пустая или слишком короткая: {len(chart1) if chart1 else 0} символов")
            except Exception as e:
                logger.error(f"Ошибка гистограммы: {e}")

        except Exception as e:
            logger.error(f"Общая ошибка создания графиков: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Статистика по источникам данных
    sources_stats = MarketOffer.objects.filter(
        city=apartment.city,
        rooms=apartment.rooms,
        is_active=True
    ).values('source').annotate(
        count=Count('id'),
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price')
    ).order_by('-count')

    debug_info = {
        'charts_available': CHARTS_AVAILABLE,
        'has_chart_generator': chart_generator is not None,
        'similar_count': len(similar_offers),
        'similar_offers_count_from_session': analysis_data.get('similar_offers_count', 0),
        'charts_created': len(charts),
        'similar_offers_sample': [
            {'price': float(offer.price), 'area': float(offer.area)}
            for offer in similar_offers[:3]
        ] if similar_offers else [],
        'charts_keys': list(charts.keys()) if charts else [],
    }

    # Логируем всю информацию
    logger.info(f"=== ОТЛАДКА analysis_results ===")
    logger.info(f"similar_offers (тип): {type(similar_offers)}")
    logger.info(f"similar_offers (длина): {len(similar_offers)}")
    logger.info(f"similar_count из сессии: {analysis_data.get('similar_offers_count', 0)}")
    logger.info(f"charts создано: {len(charts)}")
    logger.info(f"ключи charts: {list(charts.keys())}")

    if similar_offers:
        logger.info(f"Первые 3 предложения:")
        for i, offer in enumerate(similar_offers[:3]):
            logger.info(f"  {i + 1}. Цена: {offer.price}, Площадь: {offer.area}")

    if charts:
        for key in charts.keys():
            logger.info(f"График '{key}': длина {len(charts[key])} символов")

    similar_offers_list = list(similar_offers[:20]) if similar_offers else []

    return render(request, 'analyzer/analysis_results.html', {
        'apartment': apartment,
        'results': formatted_results,
        'similar_offers': similar_offers_list,  # Гарантированно список
        'similar_count': len(similar_offers_list),  # Фактическое количество
        'charts': charts,
        'sources_stats': sources_stats,
        'debug_info': debug_info,
        'title': f'Результаты анализа: {apartment.address}'
    })



@login_required
def save_analysis_report(request, apartment_id):
    """Сохранение отчета анализа в базу данных"""
    apartment = get_object_or_404(Apartment, id=apartment_id, user=request.user)

    # Получаем результаты из сессии
    analysis_data = request.session.get('analysis_results', {})

    if not analysis_data or analysis_data.get('apartment_id') != apartment.id:
        messages.error(request, 'Нет данных для сохранения отчета')
        return redirect('analyzer:analyze_apartment', apartment_id=apartment.id)

    results = analysis_data['results']

    # Проверяем, не существует ли уже отчет
    existing_report = AnalysisReport.objects.filter(apartment=apartment).first()

    if existing_report:
        # Обновляем существующий отчет
        existing_report.fair_price = results['fair_price']
        existing_report.price_difference = results['price_difference']
        existing_report.similar_offers_count = results['count']
        existing_report.avg_price_per_sqm = results['avg_price_per_sqm']
        existing_report.median_price = results['median_price']
        existing_report.min_price = results['min_price']
        existing_report.max_price = results['max_price']
        existing_report.recommendation = results['recommendation']
        existing_report.save()
        messages.success(request, 'Отчет успешно обновлен!')
    else:
        # Создаем новый отчет
        AnalysisReport.objects.create(
            apartment=apartment,
            fair_price=results['fair_price'],
            price_difference=results['price_difference'],
            similar_offers_count=results['count'],
            avg_price_per_sqm=results['avg_price_per_sqm'],
            median_price=results['median_price'],
            min_price=results['min_price'],
            max_price=results['max_price'],
            recommendation=results['recommendation'],
        )
        messages.success(request, 'Отчет успешно сохранен!')

    return redirect('analyzer:dashboard')


@login_required
def update_market_data(request):
    """Ручное обновление рыночных данных"""
    from utils.real_estate_api import data_collector

    if request.method == 'POST':
        city_id = request.POST.get('city_id')
        limit = int(request.POST.get('limit', 50))

        if city_id:
            city = get_object_or_404(City, id=city_id)
            saved_count = data_collector.update_market_data(city, limit)
            messages.success(
                request,
                f"Данные для {city.name} обновлены! Добавлено {saved_count} предложений."
            )
        else:
            # Обновляем все города
            cities = City.objects.all()
            total_saved = 0
            for city in cities:
                saved = data_collector.update_market_data(city, limit)
                total_saved += saved

            messages.success(
                request,
                f"Данные для всех городов обновлены! Всего добавлено {total_saved} предложений."
            )

        return redirect('analyzer:market_offers')

    cities = City.objects.all()
    return render(request, 'analyzer/update_data.html', {
        'cities': cities,
        'title': 'Обновление рыночных данных'
    })


# Класс-представления
class CityListView(ListView):
    """Список городов"""
    model = City
    template_name = 'analyzer/city_list.html'
    context_object_name = 'cities'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cities = City.objects.all()

        # Рассчитываем статистику в Python
        if cities.exists():
            prices = [city.avg_price_per_sqm for city in cities]
            context['avg_price_all'] = sum(prices) / len(prices)
            context['max_price'] = max(prices)
            context['min_price'] = min(prices)
            context['total_cities'] = len(cities)
        else:
            context['avg_price_all'] = 0
            context['max_price'] = 0
            context['min_price'] = 0
            context['total_cities'] = 0

        return context


class MarketOffersListView(ListView):
    """Список рыночных предложений"""
    model = MarketOffer
    template_name = 'analyzer/market_offers.html'
    context_object_name = 'offers'
    paginate_by = 10

    def get_queryset(self):
        queryset = MarketOffer.objects.filter(is_active=True)
        # Фильтрация по городу
        city_id = self.request.GET.get('city')
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        return queryset.order_by('-parsed_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # Статистика
        if queryset.exists():
            prices = [offer.price for offer in queryset]
            context['avg_price'] = sum(prices) / len(prices)
            context['min_price'] = min(prices)
            context['max_price'] = max(prices)
        else:
            context['avg_price'] = 0
            context['min_price'] = 0
            context['max_price'] = 0

        return context