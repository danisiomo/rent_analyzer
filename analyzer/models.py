import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
import uuid
logger = logging.getLogger(__name__)

class City(models.Model):
    """Модель для хранения городов"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название города',
        unique=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=False,
        verbose_name='URL-идентификатор',
        blank=True
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Широта',
        blank=True,
        null=True,
        help_text='Географическая широта центра города'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Долгота',
        blank=True,
        null=True,
        help_text='Географическая долгота центра города'
    )
    avg_price_per_sqm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Средняя цена за м² (руб.)',
        help_text='Средняя рыночная цена за квадратный метр'
    )

    population = models.IntegerField(
        verbose_name='Население',
        blank=True,
        null=True,
        help_text='Примерная численность населения'
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        help_text='Краткое описание города, районов, инфраструктуры'
    )

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']

    def save(self, *args, **kwargs):
        """Автоматически создаем slug из названия города"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (ср. цена: {self.avg_price_per_sqm} руб./м²)"


class Apartment(models.Model):
    """Модель квартиры пользователя для анализа"""

    # Типы ремонта
    REPAIR_CHOICES = [
        ('без ремонта', 'Без ремонта'),
        ('косметический', 'Косметический'),
        ('евро', 'Евроремонт'),
        ('дизайнерский', 'Дизайнерский'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='apartments'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name='Город',
        related_name='apartments'
    )
    address = models.CharField(
        max_length=255,
        verbose_name='Адрес',
        help_text='Улица, дом, корпус'
    )
    area = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Площадь (м²)',
        help_text='Общая площадь квартиры'
    )
    rooms = models.IntegerField(
        verbose_name='Количество комнат',
        choices=[(i, f"{i}-к") for i in range(1, 6)],
        default=1
    )
    floor = models.IntegerField(
        verbose_name='Этаж',
        help_text='На каком этаже находится квартира'
    )
    total_floors = models.IntegerField(
        verbose_name='Всего этажей в доме',
        help_text='Общее количество этажей в здании'
    )
    has_balcony = models.BooleanField(
        default=False,
        verbose_name='Балкон/лоджия'
    )
    repair_type = models.CharField(
        max_length=20,
        choices=REPAIR_CHOICES,
        default='косметический',
        verbose_name='Тип ремонта'
    )
    description = models.TextField(
        verbose_name='Дополнительное описание',
        blank=True,
        help_text='Дополнительные особенности квартиры'
    )
    desired_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Желаемая цена аренды (руб./мес.)',
        help_text='Цена, которую вы хотели бы получать'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Квартира'
        verbose_name_plural = 'Квартиры'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rooms}-к. квартира, {self.area} м², {self.address}"

    def get_absolute_url(self):
        return reverse('analyzer:apartment_detail', kwargs={'pk': self.pk})

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Широта',
        blank=True,
        null=True,
        help_text='Географическая широта (автоматически заполняется)'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Долгота',
        blank=True,
        null=True,
        help_text='Географическая долгота (автоматически заполняется)'
    )

    def save(self, *args, **kwargs):
        """Автоматическое геокодирование с реалистичным геокодером"""
        from utils.geocoder_realistic import geocoder  # Новый геокодер

        needs_geocoding = (
                self.address and
                (not self.latitude or not self.longitude) and
                self.city
        )

        if needs_geocoding:
            try:
                logger.info(f"Геокодирование: {self.address}")

                result = geocoder.geocode(self.address, self.city.name)

                if result:
                    self.latitude = result['lat']
                    self.longitude = result['lon']
                    logger.info(f"Координаты установлены: {self.latitude:.6f}, {self.longitude:.6f}")
                else:
                    logger.warning(f"Не удалось геокодировать, используем координаты города")
                    if self.city.latitude and self.city.longitude:
                        self.latitude = self.city.latitude
                        self.longitude = self.city.longitude

            except Exception as e:
                logger.error(f"Ошибка геокодирования: {str(e)}")

        super().save(*args, **kwargs)


class MarketOffer(models.Model):
    """Модель рыночных предложений (данные из внешних источников)"""

    SOURCE_CHOICES = [
        ('avito', 'Avito'),
        ('cian', 'ЦИАН'),
        ('yandex', 'Яндекс.Недвижимость'),
        ('mock', 'Тестовые данные'),
    ]

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name='Город',
        related_name='market_offers'
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='mock',
        verbose_name='Источник данных'
    )
    external_id = models.CharField(
        max_length=100,
        verbose_name='Внешний ID',
        help_text='Идентификатор в исходной системе',
        blank=True
    )
    address = models.CharField(
        max_length=255,
        verbose_name='Адрес'
    )
    area = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Площадь (м²)'
    )
    rooms = models.IntegerField(
        verbose_name='Количество комнат'
    )

    floor = models.IntegerField(
        verbose_name='Этаж',
        blank=True,
        null=True,
        help_text='На каком этаже находится квартира'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена аренды (руб./мес.)'
    )
    url = models.URLField(
        verbose_name='Ссылка на объявление',
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    parsed_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата получения данных'
    )
    additional_info = models.JSONField(
        verbose_name='Дополнительная информация',
        blank=True,
        null=True,
        help_text='Дополнительные параметры в JSON формате'
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Широта',
        blank=True,
        null=True,
        help_text='Географическая широта'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='Долгота',
        blank=True,
        null=True,
        help_text='Географическая долгота'
    )

    def save(self, *args, **kwargs):
        """Автоматическое геокодирование с реалистичным геокодером"""
        from utils.geocoder_realistic import geocoder  # Новый геокодер

        needs_geocoding = (
                self.address and
                (not self.latitude or not self.longitude) and
                self.city
        )

        if needs_geocoding:
            try:
                logger.info(f"Геокодирование: {self.address}")

                result = geocoder.geocode(self.address, self.city.name)

                if result:
                    self.latitude = result['lat']
                    self.longitude = result['lon']
                    logger.info(f"Координаты установлены: {self.latitude:.6f}, {self.longitude:.6f}")
                else:
                    logger.warning(f"Не удалось геокодировать, используем координаты города")
                    if self.city.latitude and self.city.longitude:
                        self.latitude = self.city.latitude
                        self.longitude = self.city.longitude

            except Exception as e:
                logger.error(f"Ошибка геокодирования: {str(e)}")

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Рыночное предложение'
        verbose_name_plural = 'Рыночные предложения'
        ordering = ['-parsed_date']
        indexes = [
            models.Index(fields=['city', 'rooms', 'area']),
            models.Index(fields=['price']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.rooms}-к., {self.area} м² - {self.price} руб. ({self.get_source_display()})"

    def price_per_sqm(self):
        """Цена за квадратный метр"""
        if self.area > 0:
            return round(self.price / self.area, 2)
        return 0


class AnalysisReport(models.Model):
    """Модель отчета анализа"""

    apartment = models.OneToOneField(
        Apartment,
        on_delete=models.CASCADE,
        verbose_name='Квартира',
        related_name='analysis_report'
    )
    fair_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Справедливая цена (руб./мес.)'
    )
    price_difference = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Разница с желаемой ценой',
        help_text='Отрицательное - цена завышена, положительное - занижена'
    )
    similar_offers_count = models.IntegerField(
        verbose_name='Количество похожих предложений'
    )
    avg_price_per_sqm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Средняя цена за м²'
    )
    median_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Медианная цена'
    )
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Минимальная цена'
    )
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Максимальная цена'
    )
    recommendation = models.TextField(
        verbose_name='Рекомендация',
        help_text='Текстовая рекомендация по ценообразованию'
    )
    chart_image = models.ImageField(
        upload_to='analysis_charts/',
        verbose_name='График анализа',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания отчета'
    )

    class Meta:
        verbose_name = 'Отчет анализа'
        verbose_name_plural = 'Отчеты анализа'
        ordering = ['-created_at']

    def __str__(self):
        return f"Отчет для {self.apartment} от {self.created_at.strftime('%d.%m.%Y')}"

    def price_range(self):
        """Возвращает диапазон цен в формате строки"""
        return f"{self.min_price} - {self.max_price} руб."

    def get_recommendation_type(self):
        """Определяет тип рекомендации"""
        if self.price_difference > 0:
            return "Цена занижена"
        elif self.price_difference < 0:
            return "Цена завышена"
        else:
            return "Цена оптимальна"