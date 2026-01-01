import report
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Count, Avg, Min, Max
from .models import Apartment, City, MarketOffer, AnalysisReport
from .forms import ApartmentForm, AnalysisFilterForm
from utils.analyzer import ApartmentAnalyzer
from utils.geocoder_simple_working import geocoder
from utils.charts import chart_generator
import logging
import numpy as np
from analyzer.models import Apartment, City, MarketOffer, AnalysisReport

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
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Получаем данные с проверкой
        cities = City.objects.all()
        cities_list = list(cities[:8])  # Преобразуем в список
        total_apartments = Apartment.objects.count()
        total_offers = MarketOffer.objects.filter(is_active=True).count()

        # Логируем для отладки
        logger.info(f"=== HOME FUNCTION DEBUG ===")
        logger.info(f"Type of cities: {type(cities)}")
        logger.info(f"Number of cities in DB: {cities.count()}")
        logger.info(f"City names: {[c.name for c in cities_list]}")
        logger.info(f"Total apartments: {total_apartments}")
        logger.info(f"Total offers: {total_offers}")

        # Проверяем есть ли данные вообще
        if cities.count() == 0:
            logger.warning("В базе нет городов!")
            # Создаем тестовые города для отладки
            test_cities = [
                ('Москва', 150000),
                ('Санкт-Петербург', 90000),
                ('Екатеринбург', 60000),
                ('Новосибирск', 55000),
            ]
            for name, price in test_cities:
                City.objects.get_or_create(name=name, defaults={'avg_price_per_sqm': price})
            cities = City.objects.all()
            cities_list = list(cities)
            logger.info(f"Созданы тестовые города: {[c.name for c in cities_list]}")

        context = {
            'cities': cities_list,  # Передаем список, а не QuerySet
            'total_apartments': total_apartments,
            'total_offers': total_offers,
        }

        return render(request, 'analyzer/home.html', context)

    except Exception as e:
        logger.error(f"Ошибка в функции home: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Возвращаем хотя бы пустой контекст при ошибке
        return render(request, 'analyzer/home.html', {
            'cities': [],
            'total_apartments': 0,
            'total_offers': 0,
        })


@login_required
def dashboard(request):
    """Личный кабинет пользователя с историей анализов"""
    # Квартиры текущего пользователя
    user_apartments = Apartment.objects.filter(user=request.user)

    # Отчеты анализа для квартир пользователя
    reports = AnalysisReport.objects.filter(apartment__user=request.user).select_related('apartment').order_by(
        '-created_at')

    # Статистика
    total_analyses = reports.count()
    successful_analyses = reports.filter(similar_offers_count__gte=3).count()

    # Последние анализы (5 штук)
    recent_analyses = reports[:5]

    context = {
        'user_apartments': user_apartments,
        'reports': reports,
        'total_analyses': total_analyses,
        'successful_analyses': successful_analyses,
        'recent_analyses': recent_analyses,
        'title': 'Личный кабинет',
    }
    return render(request, 'analyzer/dashboard.html', context)


@login_required
def view_report_detail(request, report_id):
    """Просмотр деталей конкретного отчета анализа"""
    report = get_object_or_404(AnalysisReport, id=report_id, apartment__user=request.user)

    context = {
        'report': report,
        'apartment': report.apartment,
        'title': f'Отчет анализа от {report.created_at.strftime("%d.%m.%Y %H:%M")}',
    }
    return render(request, 'analyzer/analysis_detail.html', context)

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
            # Получаем параметры анализа
            area_tolerance = float(filter_form.cleaned_data['area_tolerance'])
            price_tolerance = float(filter_form.cleaned_data['price_tolerance'])
            include_same_floor = filter_form.cleaned_data['include_same_floor']
            min_similar_offers = int(filter_form.cleaned_data['min_similar_offers'])

            # максимальное расстояние
            max_distance_km = float(filter_form.cleaned_data['max_distance'])

            # Запускаем анализ с учетом расстояния
            analyzer = ApartmentAnalyzer(apartment)
            results = analyzer.analyze(
                area_tolerance=area_tolerance,
                price_tolerance=price_tolerance,
                include_same_floor=include_same_floor,
                max_distance_km=max_distance_km,  # Передаем параметр расстояния
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

            # Добавьте сохранение фильтров и похожих предложений:
            request.session['analysis_results'] = {
                'apartment_id': apartment.id,
                'results': serializable_results,
                'similar_offers_count': results['count'],
                'filter_params': {
                    'area_tolerance': area_tolerance,
                    'price_tolerance': price_tolerance,
                    'max_distance_km': max_distance_km,
                    'include_same_floor': include_same_floor,
                },
                # Сохраняем ID похожих предложений
                'similar_offer_ids': [offer.id for offer in results.get('similar_offers', [])][:50],
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

    # Получаем параметры фильтрации из сессии
    filter_params = analysis_data.get('filter_params', {})
    area_tolerance = float(filter_params.get('area_tolerance', 20))
    price_tolerance = float(filter_params.get('price_tolerance', 30))
    max_distance_km = float(filter_params.get('max_distance_km', 10))

    # Получаем похожие предложения
    analyzer = ApartmentAnalyzer(apartment)
    similar_offers = analyzer.find_similar_offers(
        area_tolerance=area_tolerance,
        price_tolerance=price_tolerance,
        max_distance_km=max_distance_km,
        max_results=50
    )

    # Форматируем числа для отображения
    formatted_results = {
        **results,
        'avg_price': f"{results['avg_price']:,.0f}".replace(',', ' '),
        'median_price': f"{results['median_price']:,.0f}".replace(',', ' '),
        'min_price': f"{results['min_price']:,.0f}".replace(',', ' '),
        'max_price': f"{results['max_price']:,.0f}".replace(',', ' '),
        'fair_price': f"{results['fair_price']:,.0f}".replace(',', ' '),
        'price_difference': f"{results['price_difference']:+.1f}",
        'price_range': f"{results['min_price']:,.0f} - {results['max_price']:,.0f}".replace(',', ' '),
        'avg_price_per_sqm': f"{results.get('avg_price_per_sqm', 0):,.0f}".replace(',', ' '),
    }

    # Добавляем информацию о фильтрах
    formatted_results['filter_info'] = {
        'area_tolerance': area_tolerance,
        'price_tolerance': price_tolerance,
        'max_distance': max_distance_km,
        'similar_count': len(similar_offers),
    }

    # Создаем графики
    charts = {}

    # Проверяем, что есть достаточно данных
    has_enough_data = len(similar_offers) >= 3

    if has_enough_data:
        try:
            logger.info(f"Создание графиков: {len(similar_offers)} предложений")

            # Рассчитываем статистику для графиков
            import numpy as np
            prices = [float(offer.price) for offer in similar_offers]
            avg_price = np.mean(prices)
            median_price = np.median(prices)
            min_price = np.min(prices)
            max_price = np.max(prices)

            logger.info(
                f"Статистика: avg={avg_price:.0f}, median={median_price:.0f}, min={min_price:.0f}, max={max_price:.0f}")

            # Создаем простой график ГАРАНТИРОВАННО
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            import base64

            # ГРАФИК 1: Гистограмма распределения цен с отметками
            plt.figure(figsize=(12, 7))

            # Гистограмма
            n_bins = min(10, len(prices))
            counts, bins, patches = plt.hist(prices, bins=n_bins, alpha=0.7, color='skyblue', edgecolor='black',
                                             label=f'{len(prices)} предложений')

            # Цвета для столбцов гистограммы (градиент)
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            col = bin_centers - min(bin_centers)
            col /= max(col)

            for c, p in zip(col, patches):
                plt.setp(p, 'facecolor', plt.cm.viridis(c))

            # Добавляем вертикальные линии для статистики
            plt.axvline(x=avg_price, color='red', linestyle='-', linewidth=2.5,
                        label=f'Средняя цена: {avg_price:,.0f} руб.')
            plt.axvline(x=median_price, color='orange', linestyle='--', linewidth=2.5,
                        label=f'Медианная цена: {median_price:,.0f} руб.')

            # Добавляем вертикальную линию для желаемой цены
            if apartment.desired_price:
                desired_price = float(apartment.desired_price)
                plt.axvline(x=desired_price, color='green', linestyle=':', linewidth=3,
                            label=f'Ваша цена: {desired_price:,.0f} руб.')

            # Добавляем заливку между мин и макс
            plt.axvspan(min_price, max_price, alpha=0.1, color='gray',
                        label=f'Диапазон: {min_price:,.0f} - {max_price:,.0f} руб.')

            # Настройки графика
            plt.xlabel('Цена аренды (руб.)', fontsize=12, fontweight='bold')
            plt.ylabel('Количество предложений', fontsize=12, fontweight='bold')
            #plt.title(f'Распределение цен в {apartment.city.name}\n'
            #          f'Найдено {len(similar_offers)} похожих предложений',
            #          fontsize=14, fontweight='bold', pad=20)

            # Легенда с улучшенным расположением
            plt.legend(loc='upper right', fontsize=10, framealpha=0.9, shadow=True)

            # Сетка и оформление
            plt.grid(True, alpha=0.3, linestyle='--')

            # Добавляем текстовые аннотации
            stats_text = f'''Статистика:
            • Средняя цена: {avg_price:,.0f} руб.
            • Медианная цена: {median_price:,.0f} руб.
            • Минимальная: {min_price:,.0f} руб.
            • Максимальная: {max_price:,.0f} руб.
            • Количество: {len(similar_offers)} предложений'''

            plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                     fontsize=9, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            # Автоматическое форматирование оси X (тысячные разделители)
            plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

            # Сохраняем в base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            price_chart = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()

            charts['price_distribution'] = price_chart
            logger.info(f"✓ Основной график создан со статистикой (длина: {len(price_chart)})")

            # ГРАФИК 2: Точечный график цена/площадь (опционально)
            if len(similar_offers) >= 5:
                plt.figure(figsize=(12, 7))
                areas = [float(offer.area) for offer in similar_offers]
                prices = [float(offer.price) for offer in similar_offers]

                # Точечный график
                scatter = plt.scatter(areas, prices, alpha=0.7, color='green', s=100,
                                      edgecolors='black', linewidth=0.5)

                # Линии регрессии
                try:
                    z = np.polyfit(areas, prices, 1)
                    p = np.poly1d(z)
                    plt.plot(areas, p(areas), "r--", alpha=0.8, linewidth=2,
                             label=f'Тренд: y = {z[0]:.1f}x + {z[1]:.1f}')
                except:
                    pass

                # Добавляем точку для анализируемой квартиры
                if apartment.area and apartment.desired_price:
                    plt.scatter(float(apartment.area), float(apartment.desired_price),
                                color='red', s=300, marker='*', edgecolors='black', linewidth=2,
                                label=f'Ваша квартира: {float(apartment.area)} м², {float(apartment.desired_price):,.0f} руб.')

                # Средние линии
                mean_area = np.mean(areas)
                mean_price = np.mean(prices)
                plt.axhline(y=mean_price, color='blue', linestyle=':', alpha=0.5,
                            label=f'Ср. цена: {mean_price:,.0f} руб.')
                plt.axvline(x=mean_area, color='blue', linestyle=':', alpha=0.5,
                            label=f'Ср. площадь: {mean_area:.1f} м²')

                # Настройки
                plt.xlabel('Площадь (м²)', fontsize=12, fontweight='bold')
                plt.ylabel('Цена (руб.)', fontsize=12, fontweight='bold')
                plt.title(f'Зависимость цены от площади в {apartment.city.name}',
                          fontsize=14, fontweight='bold', pad=20)

                # Форматирование осей
                plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

                plt.legend(loc='upper left', fontsize=9)
                plt.grid(True, alpha=0.3, linestyle='--')

                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
                buffer.seek(0)
                scatter_chart = base64.b64encode(buffer.getvalue()).decode()
                buffer.close()
                plt.close()

                charts['price_vs_area'] = scatter_chart
                logger.info(f"✓ Точечный график создан")

        except Exception as e:
            logger.error(f"Ошибка создания графиков: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ОБНОВЛЯЕМ СЕССИЮ с графиками перед отображением
    analysis_data['charts'] = charts
    request.session['analysis_results'] = analysis_data
    request.session.modified = True

    # Логируем информацию
    logger.info(f"=== ОТЛАДКА analysis_results (после создания) ===")
    logger.info(f"similar_offers: {len(similar_offers)} предложений")
    logger.info(f"charts создано: {len(charts)}")
    logger.info(f"ключи charts: {list(charts.keys())}")
    if charts:
        for key in charts.keys():
            logger.info(f"График '{key}': длина {len(charts[key])} символов")

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

    return render(request, 'analyzer/analysis_results.html', {
        'apartment': apartment,
        'results': formatted_results,
        'similar_offers': similar_offers[:20],  # Показываем только 20 для производительности
        'similar_count': len(similar_offers),
        'charts': charts,
        'title': f'Результаты анализа: {apartment.address}'
    })

@login_required
def apartment_detail(request, pk):
    """Детальная информация о квартире"""
    apartment = get_object_or_404(Apartment, pk=pk, user=request.user)
    report = apartment.analysis_report if hasattr(apartment, 'analysis_report') else None

    # Статистика по этой квартире
    analysis_count = AnalysisReport.objects.filter(apartment=apartment).count()

    # Похожие предложения в этом городе
    similar_in_city = MarketOffer.objects.filter(
        city=apartment.city,
        rooms=apartment.rooms,
        is_active=True
    )[:5]

    context = {
        'apartment': apartment,
        'report': report,
        'analysis_count': analysis_count,
        'similar_in_city': similar_in_city,
        'title': f'Квартира: {apartment.address}',
    }

    return render(request, 'analyzer/apartment_detail.html', context)


@login_required
def delete_apartment(request, pk):
    """Удаление квартиры"""
    apartment = get_object_or_404(Apartment, pk=pk, user=request.user)

    if request.method == 'POST':
        address = apartment.address
        apartment.delete()
        messages.success(request, f'Квартира "{address}" удалена')
        return redirect('analyzer:dashboard')

    return render(request, 'analyzer/confirm_delete.html', {
        'object': apartment,
        'object_type': 'квартиру',
        'title': f'Удаление квартиры: {apartment.address}',
        'cancel_url': 'analyzer:apartment_detail',
        'cancel_kwargs': {'pk': apartment.id},
    })


@login_required
def delete_report(request, pk):
    """Удаление отчета анализа"""
    report = get_object_or_404(AnalysisReport, pk=pk, apartment__user=request.user)

    if request.method == 'POST':
        apartment_address = report.apartment.address
        report.delete()
        messages.success(request, f'Отчет анализа для квартиры "{apartment_address}" удален')
        return redirect('analyzer:dashboard')

    return render(request, 'analyzer/confirm_delete.html', {
        'object': report,
        'object_type': 'отчет анализа',
        'title': f'Удаление отчета анализа',
        'cancel_url': 'analyzer:analysis_detail',
        'cancel_kwargs': {'pk': report.id},
    })


@login_required
def analysis_detail(request, pk):
    """Детальная информация об отчете анализа"""
    report = get_object_or_404(AnalysisReport, pk=pk, apartment__user=request.user)

    # Отладочная информация
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== DEBUG analysis_detail ===")
    logger.info(f"Report ID: {report.id}")
    logger.info(f"Has chart_image_base64: {bool(report.chart_image_base64)}")
    logger.info(f"Chart base64 length: {len(report.chart_image_base64) if report.chart_image_base64 else 0}")

    context = {
        'report': report,
        'apartment': report.apartment,
        'title': f'Отчет анализа: {report.apartment.address}',
    }

    return render(request, 'analyzer/analysis_detail.html', context)

@login_required
def save_analysis_report(request, apartment_id):
    """Сохранение отчета анализа в базу данных с графиком"""
    apartment = get_object_or_404(Apartment, id=apartment_id, user=request.user)

    # Получаем результаты из сессии
    analysis_data = request.session.get('analysis_results', {})

    if not analysis_data or analysis_data.get('apartment_id') != apartment.id:
        messages.error(request, 'Нет данных для сохранения отчета')
        return redirect('analyzer:analyze_apartment', apartment_id=apartment.id)

    results = analysis_data['results']

    # Получаем график из сессии
    charts_data = analysis_data.get('charts', {})
    chart_image_base64 = charts_data.get('price_distribution') if charts_data else None

    # Отладочная информация
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== DEBUG save_analysis_report ===")
    logger.info(f"Has charts data: {bool(charts_data)}")
    logger.info(f"Chart keys: {list(charts_data.keys()) if charts_data else 'No charts'}")
    logger.info(f"Chart base64 length: {len(chart_image_base64) if chart_image_base64 else 0}")

    # Проверяем, не существует ли уже отчет
    existing_report = AnalysisReport.objects.filter(apartment=apartment).first()

    if existing_report:
        # Обновляем существующий отчет
        existing_report.fair_price = results['fair_price']
        existing_report.price_difference = results['price_difference']
        existing_report.similar_offers_count = results['count']
        existing_report.avg_price_per_sqm = results.get('avg_price_per_sqm', 0)
        existing_report.avg_price = results.get('avg_price', 0)
        existing_report.median_price = results.get('median_price', 0)
        existing_report.min_price = results.get('min_price', 0)
        existing_report.max_price = results.get('max_price', 0)
        existing_report.recommendation = results['recommendation']

        # Сохраняем график как base64
        if chart_image_base64:
            existing_report.chart_image_base64 = chart_image_base64
            logger.info(f"✓ График сохранен в существующий отчет (длина: {len(chart_image_base64)})")
        else:
            logger.warning("⚠ График не найден в сессии")

        existing_report.save()
        messages.success(request, 'Отчет успешно обновлен с графиком!')
    else:
        # Создаем новый отчет
        report = AnalysisReport(
            apartment=apartment,
            fair_price=results['fair_price'],
            price_difference=results['price_difference'],
            similar_offers_count=results['count'],
            avg_price_per_sqm=results.get('avg_price_per_sqm', 0),
            avg_price=results.get('avg_price', 0),
            median_price=results.get('median_price', 0),
            min_price=results.get('min_price', 0),
            max_price=results.get('max_price', 0),
            recommendation=results['recommendation'],
        )

        # Сохраняем график как base64
        if chart_image_base64:
            report.chart_image_base64 = chart_image_base64
            logger.info(f"✓ График сохранен в новый отчет (длина: {len(chart_image_base64)})")
        else:
            logger.warning("⚠ График не найден в сессии при создании отчета")

        report.save()
        messages.success(request, 'Отчет успешно сохранен с графиком!')

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
    """Список рыночных предложений с фильтрами"""
    model = MarketOffer
    template_name = 'analyzer/market_offers.html'
    context_object_name = 'offers'
    paginate_by = 20

    def get_queryset(self):
        queryset = MarketOffer.objects.filter(is_active=True)

        # Получаем параметры фильтрации
        city_id = self.request.GET.get('city')
        rooms = self.request.GET.get('rooms')
        source = self.request.GET.get('source')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        sort_by = self.request.GET.get('sort_by', '-parsed_date')  # Сортировка

        # Применяем фильтры
        if city_id and city_id != 'all':
            queryset = queryset.filter(city_id=city_id)

        if rooms and rooms != 'all':
            queryset = queryset.filter(rooms=int(rooms))

        if source and source != 'all':
            queryset = queryset.filter(source=source)

        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except:
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except:
                pass

        # Применяем сортировку
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'area_asc':
            queryset = queryset.order_by('area')
        elif sort_by == 'area_desc':
            queryset = queryset.order_by('-area')
        elif sort_by == 'date_asc':
            queryset = queryset.order_by('parsed_date')
        else:  # date_desc или по умолчанию
            queryset = queryset.order_by('-parsed_date')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # Статистика
        if queryset.exists():
            prices = [float(offer.price) for offer in queryset]
            context['avg_price'] = sum(prices) / len(prices)
            context['min_price'] = min(prices)
            context['max_price'] = max(prices)
        else:
            context['avg_price'] = 0
            context['min_price'] = 0
            context['max_price'] = 0

        context['total_offers'] = queryset.count()
        context['cities'] = City.objects.all()
        context['rooms_list'] = [1, 2, 3, 4, 5]
        context['sources'] = MarketOffer.SOURCE_CHOICES

        # Текущие значения фильтров
        context['current_city'] = self.request.GET.get('city', '')
        context['current_rooms'] = self.request.GET.get('rooms', '')
        context['current_source'] = self.request.GET.get('source', '')
        context['current_min_price'] = self.request.GET.get('min_price', '')
        context['current_max_price'] = self.request.GET.get('max_price', '')
        context['current_sort'] = self.request.GET.get('sort_by', 'date_desc')

        return context
