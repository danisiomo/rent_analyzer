from django import forms
from django.core.exceptions import ValidationError
from .models import Apartment, City


class ApartmentForm(forms.ModelForm):
    """Форма для добавления квартиры пользователем"""

    class Meta:
        model = Apartment
        fields = [
            'city', 'address', 'area', 'rooms',
            'floor', 'total_floors', 'has_balcony',
            'repair_type', 'description', 'desired_price'
        ]
        widgets = {
            'city': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Улица, дом, корпус'
            }),
            'area': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 45.5',
                'step': '0.1',
                'min': '10'
            }),
            'rooms': forms.Select(attrs={'class': 'form-select'}, choices=[
                (1, '1-к'), (2, '2-к'), (3, '3-к'), (4, '4-к'), (5, '5+ к')
            ]),
            'floor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'На каком этаже',
                'min': '1'
            }),
            'total_floors': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Всего этажей в доме',
                'min': '1'
            }),
            'has_balcony': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'repair_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительные особенности квартиры...'
            }),
            'desired_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Желаемая цена аренды в рублях',
                'step': '1000',
                'min': '1000'
            }),
        }
        labels = {
            'city': 'Город',
            'address': 'Адрес',
            'area': 'Площадь (м²)',
            'rooms': 'Количество комнат',
            'floor': 'Этаж',
            'total_floors': 'Всего этажей в доме',
            'has_balcony': 'Есть балкон/лоджия',
            'repair_type': 'Тип ремонта',
            'description': 'Дополнительное описание',
            'desired_price': 'Желаемая цена аренды (руб./мес.)',
        }
        help_texts = {
            'area': 'Общая площадь квартиры в квадратных метрах',
            'desired_price': 'Цена, которую вы хотели бы получать за аренду',
        }

    def clean_area(self):
        """Валидация площади"""
        area = self.cleaned_data['area']
        if area <= 0:
            raise ValidationError('Площадь должна быть положительным числом')
        if area > 1000:
            raise ValidationError('Площадь не может превышать 1000 м²')
        return area

    def clean_floor(self):
        """Валидация этажа"""
        floor = self.cleaned_data['floor']
        total_floors = self.cleaned_data.get('total_floors')

        if floor <= 0:
            raise ValidationError('Этаж должен быть положительным числом')

        if total_floors and floor > total_floors:
            raise ValidationError('Этаж не может быть больше общего количества этажей')

        return floor

    def clean_desired_price(self):
        """Валидация цены"""
        price = self.cleaned_data['desired_price']
        if price <= 0:
            raise ValidationError('Цена должна быть положительным числом')
        if price > 10000000:  # 10 миллионов
            raise ValidationError('Цена слишком высока')
        return price


class AnalysisFilterForm(forms.Form):
    """Форма для фильтрации похожих предложений"""

    AREA_TOLERANCE_CHOICES = [
        (10, '±10%'),
        (20, '±20%'),
        (30, '±30%'),
        (40, '±40%'),
        (50, '±50%'),
    ]

    PRICE_TOLERANCE_CHOICES = [
        (20, '±20%'),
        (30, '±30%'),
        (40, '±40%'),
        (50, '±50%'),
        (100, '±100%'),
    ]

    # НОВЫЙ ПАРАМЕТР:
    MAX_DISTANCE_CHOICES = [
        (1, '1 км (очень близко)'),
        (3, '3 км (рядом)'),
        (5, '5 км (недалеко)'),
        (10, '10 км (в пределах района)'),
        (20, '20 км (в пределах города)'),
        (50, '50 км (без ограничений по расстоянию)'),
    ]

    area_tolerance = forms.ChoiceField(
        choices=AREA_TOLERANCE_CHOICES,
        initial=20,
        label='Допустимое отклонение по площади',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    price_tolerance = forms.ChoiceField(
        choices=PRICE_TOLERANCE_CHOICES,
        initial=30,
        label='Допустимое отклонение по цене',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # НОВОЕ ПОЛЕ:
    max_distance = forms.ChoiceField(
        choices=MAX_DISTANCE_CHOICES,
        initial=10,
        label='Максимальное расстояние от вашей квартиры',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    include_same_floor = forms.BooleanField(
        required=False,
        initial=False,
        label='Учитывать только тот же этаж',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    min_similar_offers = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=3,
        label='Минимальное количество похожих предложений',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )