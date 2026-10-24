from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    DateInput,
    EmailField,
    Form,
    ModelChoiceField,
    ModelForm,
    PasswordInput,
)

from catalog.models import Category

from .models import Account, SpecialistProfile, UserProfile


class LoginForm(Form):
    email = EmailField(label="Почта")
    password = CharField(label="Пароль", widget=PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise ValidationError("Неверная почта или пароль")
            self.user = user
        return cleaned


class CustomerRegistrationForm(Form):
    email = EmailField(label="Почта")
    password1 = CharField(label="Пароль", widget=PasswordInput)
    password2 = CharField(label="Пароль ещё раз", widget=PasswordInput)
    first_name = CharField(label="Имя", max_length=100)
    last_name = CharField(label="Фамилия", max_length=100)
    patronymic = CharField(label="Отчество", max_length=100, required=False)
    phone = CharField(label="Телефон", max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean_email(self):
        email = Account.objects.normalize_email(self.cleaned_data["email"])
        if Account.objects.filter(email__iexact=email).exists():
            raise ValidationError("Такая почта уже зарегистрирована")
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают")
        return cleaned

    def save(self):
        account = Account.objects.create_user(
            self.cleaned_data["email"],
            self.cleaned_data["password1"],
            role=Account.Role.CUSTOMER,
        )
        UserProfile.objects.create(
            account=account,
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            patronymic=self.cleaned_data["patronymic"],
            phone=self.cleaned_data["phone"],
            city="Минск",
        )
        return account


class SpecialistRegistrationForm(CustomerRegistrationForm):
    category = ModelChoiceField(label="Категория", queryset=Category.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_hidden=False)
        self.fields["category"].empty_label = "Выберите категорию"
        self.fields["category"].widget.attrs["class"] = "input"

    def save(self):
        account = Account.objects.create_user(
            self.cleaned_data["email"],
            self.cleaned_data["password1"],
            role=Account.Role.SPECIALIST,
        )
        SpecialistProfile.objects.create(
            account=account,
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            patronymic=self.cleaned_data["patronymic"],
            phone=self.cleaned_data["phone"],
            city="Минск",
            category=self.cleaned_data["category"],
        )
        return account


class ProfileForm(ModelForm):
    class Meta:
        fields = [
            "first_name",
            "last_name",
            "patronymic",
            "birth_date",
            "phone",
            "photo",
            "instagram",
            "telegram",
            "pinterest",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"
        self.fields["birth_date"].widget = DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "class": "input"},
        )
        self.fields["birth_date"].input_formats = ["%Y-%m-%d"]


class UserProfileForm(ProfileForm):
    class Meta(ProfileForm.Meta):
        model = UserProfile


class SpecialistProfileForm(ProfileForm):
    class Meta(ProfileForm.Meta):
        model = SpecialistProfile
