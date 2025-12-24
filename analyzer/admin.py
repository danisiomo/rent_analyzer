from django.contrib import admin
from django.utils.html import format_html
from .models import City, Apartment, MarketOffer, AnalysisReport


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'avg_price_per_sqm', 'population', 'apartments_count')
    list_filter = ('name',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def apartments_count(self, obj):
        return obj.apartments.count()

    apartments_count.short_description = 'Количество квартир'


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'city', 'area', 'rooms',
        'floor', 'desired_price', 'user', 'created_at'
    )
    list_filter = ('city', 'rooms', 'has_balcony', 'repair_type')
    search_fields = ('address', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'city', 'address', 'area', 'rooms')
        }),
        ('Детали квартиры', {
            'fields': ('floor', 'total_floors', 'has_balcony', 'repair_type')
        }),
        ('Финансы', {
            'fields': ('desired_price',)
        }),
        ('Дополнительно', {
            'fields': ('description', 'created_at', 'updated_at')
        }),
    )


@admin.register(MarketOffer)
class MarketOfferAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'city', 'area', 'rooms',
        'price', 'price_per_sqm_display', 'source', 'is_active', 'parsed_date'
    )
    list_filter = ('city', 'source', 'is_active', 'rooms')
    search_fields = ('address', 'external_id')
    readonly_fields = ('parsed_date',)
    list_editable = ('is_active',)

    def price_per_sqm_display(self, obj):
        return f"{obj.price_per_sqm()} руб./м²"

    price_per_sqm_display.short_description = 'Цена за м²'


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = (
        'apartment', 'fair_price', 'price_difference',
        'similar_offers_count', 'get_recommendation_type', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('apartment__address', 'recommendation')
    readonly_fields = ('created_at',)

    def get_recommendation_type(self, obj):
        return obj.get_recommendation_type()

    get_recommendation_type.short_description = 'Рекомендация'