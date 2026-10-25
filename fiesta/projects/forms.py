from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    DateField,
    DateInput,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Textarea,
)
from django.utils import timezone

from catalog.models import EventType

from .models import Project, Review


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ["event_type", "title", "event_date", "description"]
        widgets = {
            "description": Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_date"].widget = DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "class": "input"},
        )
        self.fields["event_date"].input_formats = ["%Y-%m-%d"]
        self.fields["event_type"].empty_label = "Выберите тип"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class AddSpecialistForm(Form):
    project = ModelChoiceField(
        label="Проект",
        required=False,
        queryset=Project.objects.none(),
    )
    title = CharField(label="Название проекта", required=False, max_length=200)
    event_type = ModelChoiceField(
        label="Мероприятие",
        required=False,
        queryset=EventType.objects.none(),
    )
    event_date = DateField(label="Дата", required=False)

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(
            owner=owner,
            status=Project.Status.IN_PROGRESS,
        )
        self.fields["project"].empty_label = "Создать новый"
        self.fields["event_type"].queryset = EventType.objects.all()
        self.fields["event_type"].empty_label = "Выберите тип"
        self.fields["title"].widget.attrs["placeholder"] = "Название проекта"
        self.fields["event_date"].widget = DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "class": "input"},
        )
        self.fields["event_date"].input_formats = ["%Y-%m-%d"]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean(self):
        data = super().clean()
        if data.get("project"):
            return data
        if not data.get("title") or not data.get("event_type") or not data.get("event_date"):
            raise ValidationError(
                "Выберите проект или заполните название, мероприятие и дату"
            )
        return data


class ReviewForm(ModelForm):
    rating = IntegerField(label="Оценка", min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ["rating", "text"]
        widgets = {"text": Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class ReplyForm(ModelForm):
    class Meta:
        model = Review
        fields = ["reply"]
        widgets = {"reply": Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reply"].widget.attrs["class"] = "input"

    def save(self, commit=True):
        review = super().save(commit=False)
        review.reply_at = timezone.now()
        if commit:
            review.save()
        return review
