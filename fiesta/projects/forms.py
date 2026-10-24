from django.forms import (
    CharField,
    DateInput,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Textarea,
)
from django.utils import timezone

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


class SelectSpecialistForm(Form):
    project = ModelChoiceField(label="Проект", queryset=Project.objects.none())
    role_title = CharField(label="Роль", max_length=100)

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(
            owner=owner,
            status=Project.Status.IN_PROGRESS,
        )
        self.fields["project"].empty_label = "Выберите проект"
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"


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
