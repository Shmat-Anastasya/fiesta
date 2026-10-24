from django.forms import (
    CharField,
    ChoiceField,
    DateInput,
    DecimalField,
    Form,
    ModelChoiceField,
    ModelForm,
)

from accounts.models import SpecialistProfile

from .models import Category


class CatalogFilterForm(Form):
    category = ModelChoiceField(
        label="Категория",
        required=False,
        queryset=Category.objects.none(),
        empty_label="Все категории",
    )
    price_mode = ChoiceField(
        label="Цена",
        required=False,
        choices=[
            ("", "Любая"),
            ("service", "За услугу"),
            ("hour", "За час"),
        ],
    )
    price_max = DecimalField(
        label="До, бел. руб.",
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
    )
    sort = ChoiceField(
        label="Сортировка",
        required=False,
        choices=[
            ("rating", "По рейтингу"),
            ("price", "По цене, сначала дешевле"),
            ("price_desc", "По цене, сначала дороже"),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_hidden=False)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"


class QuestionnaireForm(ModelForm):
    class Meta:
        model = SpecialistProfile
        fields = ["category", "description", "career_start"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_hidden=False)
        self.fields["category"].empty_label = None
        self.fields["description"].widget.attrs["maxlength"] = 2000
        self.fields["career_start"].widget = DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "class": "input"},
        )
        self.fields["career_start"].input_formats = ["%Y-%m-%d"]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean_description(self):
        text = self.cleaned_data["description"]
        if len(text) > 2000:
            self.add_error("description", "Описание не длиннее 2000 символов")
        return text


class PortfolioForm(Form):
    album_title = CharField(label="Название альбома", max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["album_title"].widget.attrs["class"] = "input"
