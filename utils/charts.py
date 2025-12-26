"""
Модуль для создания графиков и визуализаций для RentAnalyzer
"""
import matplotlib

matplotlib.use('Agg')  # Для работы без GUI
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from typing import List, Dict, Optional
from django.db.models import QuerySet
from analyzer.models import MarketOffer
import logging

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Генератор графиков для визуализации данных аренды"""

    @staticmethod
    def create_price_distribution_chart(offers: QuerySet or List[MarketOffer],
                                        apartment_price: float = None,
                                        title: str = "Распределение цен на рынке") -> str:
        """
        Создает гистограмму распределения цен с выделением цены пользователя

        Args:
            offers: Список или QuerySet предложений
            apartment_price: Цена квартиры пользователя (опционально)
            title: Заголовок графика

        Returns:
            Base64 строка с изображением графика
        """
        try:
            # Извлекаем цены
            if isinstance(offers, QuerySet):
                prices = [float(offer.price) for offer in offers]
            else:
                prices = [float(offer.price) for offer in offers]

            if len(prices) < 3:
                return ""

            # Создаем график
            plt.figure(figsize=(10, 6), dpi=100)
            plt.style.use('seaborn-v0_8-whitegrid')

            # Определяем оптимальное количество бинов
            n_bins = min(15, max(5, len(prices) // 5))

            # Гистограмма
            n, bins, patches = plt.hist(prices, bins=n_bins, alpha=0.7,
                                        color='#4A90E2', edgecolor='black', linewidth=1.2)

            # Средняя и медианная цена
            avg_price = np.mean(prices)
            median_price = np.median(prices)

            plt.axvline(avg_price, color='#FF6B6B', linestyle='--', linewidth=2.5,
                        alpha=0.8, label=f'Средняя: {avg_price:,.0f} руб.')
            plt.axvline(median_price, color='#51CF66', linestyle='-.', linewidth=2.5,
                        alpha=0.8, label=f'Медианная: {median_price:,.0f} руб.')

            # Цена пользователя (если указана)
            if apartment_price:
                plt.axvline(apartment_price, color='#FFD93D', linestyle='-', linewidth=3,
                            alpha=0.9, label=f'Ваша цена: {apartment_price:,.0f} руб.')

            # Настройки графика
            plt.xlabel('Цена аренды, руб.', fontsize=12, fontweight='bold')
            plt.ylabel('Количество предложений', fontsize=12, fontweight='bold')
            plt.title(title, fontsize=14, fontweight='bold', pad=20)
            plt.legend(loc='upper right', fontsize=10)
            plt.grid(True, alpha=0.3, linestyle='--')

            # Форматирование оси X
            plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
            plt.xticks(rotation=45)

            plt.tight_layout()

            # Конвертируем в base64
            return ChartGenerator._fig_to_base64()

        except Exception as e:
            logger.error(f"Ошибка создания гистограммы: {e}")
            return ""

    @staticmethod
    def create_price_vs_area_scatter(offers: QuerySet or List[MarketOffer],
                                     apartment_area: float = None,
                                     apartment_price: float = None,
                                     title: str = "Зависимость цены от площади") -> str:
        """
        Создает scatter plot зависимости цены от площади

        Args:
            offers: Предложения
            apartment_area: Площадь квартиры пользователя
            apartment_price: Цена квартиры пользователя
            title: Заголовок графика
        """
        try:
            if isinstance(offers, QuerySet):
                areas = [float(offer.area) for offer in offers]
                prices = [float(offer.price) for offer in offers]
            else:
                areas = [float(offer.area) for offer in offers]
                prices = [float(offer.price) for offer in offers]

            if len(areas) < 3 or len(prices) < 3:
                return ""

            plt.figure(figsize=(10, 6), dpi=100)
            plt.style.use('seaborn-v0_8-whitegrid')

            # Scatter plot
            scatter = plt.scatter(areas, prices, alpha=0.6, color='#4A90E2',
                                  s=80, edgecolors='white', linewidth=0.5)

            # Линия регрессии
            if len(areas) > 1:
                z = np.polyfit(areas, prices, 1)
                p = np.poly1d(z)
                x_range = np.linspace(min(areas), max(areas), 100)
                plt.plot(x_range, p(x_range), "r--", alpha=0.8, linewidth=2.5,
                         label=f'Тренд: {z[0]:.0f} руб./м²')

            # Квартира пользователя (если указана)
            if apartment_area and apartment_price:
                plt.scatter([apartment_area], [apartment_price], color='#FFD93D',
                            s=200, edgecolors='black', linewidth=2, zorder=5,
                            label='Ваша квартира')

            plt.xlabel('Площадь, м²', fontsize=12, fontweight='bold')
            plt.ylabel('Цена аренды, руб.', fontsize=12, fontweight='bold')
            plt.title(title, fontsize=14, fontweight='bold', pad=20)
            plt.legend(loc='upper left', fontsize=10)
            plt.grid(True, alpha=0.3, linestyle='--')

            # Форматирование оси Y
            plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

            plt.tight_layout()

            return ChartGenerator._fig_to_base64()

        except Exception as e:
            logger.error(f"Ошибка создания scatter plot: {e}")
            return ""

    @staticmethod
    def create_price_comparison_chart(apartment_price: float, market_stats: Dict,
                                      title: str = "Сравнение с рыночными показателями") -> str:
        """
        Создает столбчатую диаграмму сравнения цены квартиры с рыночными показателями

        Args:
            apartment_price: Цена квартиры пользователя
            market_stats: Словарь с рыночной статистикой
            title: Заголовок графика
        """
        try:
            plt.figure(figsize=(10, 6), dpi=100)
            plt.style.use('seaborn-v0_8-whitegrid')

            # Данные для сравнения
            labels = ['Ваша цена', 'Средняя', 'Медианная', 'Минимальная', 'Максимальная']
            values = [
                apartment_price,
                float(market_stats.get('avg_price', 0)),
                float(market_stats.get('median_price', 0)),
                float(market_stats.get('min_price', 0)),
                float(market_stats.get('max_price', 0))
            ]

            # Цвета
            colors = ['#FFD93D', '#4A90E2', '#51CF66', '#94D82D', '#FF6B6B']

            # Столбчатая диаграмма
            bars = plt.bar(labels, values, color=colors, alpha=0.8,
                           edgecolor='black', linewidth=1.5)

            # Добавляем значения на столбцы
            for bar, value in zip(bars, values):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width() / 2., height + height * 0.01,
                         f'{value:,.0f}', ha='center', va='bottom',
                         fontsize=10, fontweight='bold')

            plt.ylabel('Цена, руб.', fontsize=12, fontweight='bold')
            plt.title(title, fontsize=14, fontweight='bold', pad=20)
            plt.ylim(0, max(values) * 1.15)
            plt.grid(True, alpha=0.3, linestyle='--', axis='y')

            # Форматирование оси Y
            plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

            plt.tight_layout()

            return ChartGenerator._fig_to_base64()

        except Exception as e:
            logger.error(f"Ошибка создания диаграммы сравнения: {e}")
            return ""

    @staticmethod
    def create_price_per_sqm_chart(offers: QuerySet or List[MarketOffer],
                                   apartment_price_per_sqm: float = None,
                                   title: str = "Цена за квадратный метр") -> str:
        """
        Создает box plot цены за м² по количеству комнат

        Args:
            offers: Предложения
            apartment_price_per_sqm: Цена за м² квартиры пользователя
            title: Заголовок графика
        """
        try:
            if isinstance(offers, QuerySet):
                data_dict = {}
                for offer in offers:
                    rooms = offer.rooms
                    price_per_sqm = float(offer.price) / float(offer.area) if offer.area > 0 else 0
                    if rooms not in data_dict:
                        data_dict[rooms] = []
                    data_dict[rooms].append(price_per_sqm)
            else:
                data_dict = {}
                for offer in offers:
                    rooms = offer['rooms']
                    price_per_sqm = float(offer['price']) / float(offer['area']) if offer['area'] > 0 else 0
                    if rooms not in data_dict:
                        data_dict[rooms] = []
                    data_dict[rooms].append(price_per_sqm)

            if not data_dict:
                return ""

            # Подготовка данных для box plot
            rooms_list = sorted(data_dict.keys())
            price_data = [data_dict[rooms] for rooms in rooms_list]
            room_labels = [f'{rooms}-к' for rooms in rooms_list]

            plt.figure(figsize=(10, 6), dpi=100)
            plt.style.use('seaborn-v0_8-whitegrid')

            # Box plot
            box = plt.boxplot(price_data, labels=room_labels, patch_artist=True,
                              medianprops=dict(color='black', linewidth=2),
                              whiskerprops=dict(color='gray', linewidth=1.5),
                              capprops=dict(color='gray', linewidth=1.5))

            # Настройка цветов
            colors = ['#4A90E2', '#51CF66', '#FFD93D', '#FF6B6B', '#9B59B6']
            for patch, color in zip(box['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            # Цена пользователя (если указана)
            if apartment_price_per_sqm:
                plt.axhline(y=apartment_price_per_sqm, color='#E74C3C',
                            linestyle='--', linewidth=2.5, alpha=0.8,
                            label=f'Ваша цена: {apartment_price_per_sqm:.0f} руб./м²')
                plt.legend(loc='upper right', fontsize=10)

            plt.xlabel('Количество комнат', fontsize=12, fontweight='bold')
            plt.ylabel('Цена за м², руб.', fontsize=12, fontweight='bold')
            plt.title(title, fontsize=14, fontweight='bold', pad=20)
            plt.grid(True, alpha=0.3, linestyle='--', axis='y')

            plt.tight_layout()

            return ChartGenerator._fig_to_base64()

        except Exception as e:
            logger.error(f"Ошибка создания box plot: {e}")
            return ""

    @staticmethod
    def create_market_analysis_dashboard(apartment, similar_offers, market_stats) -> Dict:
        """
        Создает комплексную дашборд-визуализацию анализа

        Returns:
            Словарь с base64 изображениями всех графиков
        """
        charts = {}

        try:
            # 1. Распределение цен
            charts['price_distribution'] = ChartGenerator.create_price_distribution_chart(
                similar_offers,
                apartment_price=float(apartment.desired_price),
                title=f"Распределение цен на {apartment.rooms}-к квартиры в {apartment.city.name}"
            )

            # 2. Зависимость цены от площади
            charts['price_vs_area'] = ChartGenerator.create_price_vs_area_scatter(
                similar_offers,
                apartment_area=float(apartment.area),
                apartment_price=float(apartment.desired_price),
                title=f"Зависимость цены от площади в {apartment.city.name}"
            )

            # 3. Сравнение с рынком
            charts['price_comparison'] = ChartGenerator.create_price_comparison_chart(
                float(apartment.desired_price),
                market_stats,
                title=f"Сравнение вашей цены с рыночными показателями"
            )

            # 4. Цена за м²
            apartment_price_per_sqm = float(apartment.desired_price) / float(
                apartment.area) if apartment.area > 0 else 0
            charts['price_per_sqm'] = ChartGenerator.create_price_per_sqm_chart(
                similar_offers,
                apartment_price_per_sqm=apartment_price_per_sqm,
                title=f"Цена за квадратный метр в {apartment.city.name}"
            )

        except Exception as e:
            logger.error(f"Ошибка создания дашборда: {e}")

        return charts

    @staticmethod
    def _fig_to_base64() -> str:
        """Конвертирует текущий график в base64 строку"""
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()

        return base64.b64encode(image_png).decode('utf-8')


# Глобальный экземпляр
chart_generator = ChartGenerator()