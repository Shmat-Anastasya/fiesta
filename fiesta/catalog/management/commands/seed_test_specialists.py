from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Account, SpecialistProfile, UserProfile
from catalog.models import Category, CategoryPriceField, EventType, SpecialistPrice
from projects.models import Project, Review, RoleCandidate

PASSWORD = "Test-fiesta-2026"

SPECIALISTS = [
    ("test.photo@fiesta.local", "Фотограф", {"event": "500", "hour": "50"}),
    ("test.video@fiesta.local", "Видеограф", {"event": "800", "hour": "80"}),
    ("test.host@fiesta.local", "Ведущий", {"event": "400", "hour": "40"}),
    ("test.catering@fiesta.local", "Кейтеринг", {"person": "35"}),
    ("test.venue@fiesta.local", "Площадка", {"day": "1200"}),
    ("test.decor@fiesta.local", "Декоратор", {"event": "300"}),
]


class Command(BaseCommand):
    help = "Создаёт тестовых специалистов с ценами. Повторный запуск не плодит записи."

    def handle(self, *args, **options):
        profiles = {}
        for email, category_name, prices in SPECIALISTS:
            category = Category.objects.filter(name=category_name).first()
            if category is None:
                self.stdout.write(f"Нет категории {category_name}")
                continue
            account, created = Account.objects.get_or_create(
                email=email,
                defaults={"role": Account.Role.SPECIALIST},
            )
            if not created and account.role != Account.Role.SPECIALIST:
                self.stdout.write(f"Почта занята: {email}")
                continue
            account.role = Account.Role.SPECIALIST
            account.set_password(PASSWORD)
            account.save()
            profile, _ = SpecialistProfile.objects.get_or_create(
                account=account,
                defaults={
                    "first_name": "Тест",
                    "last_name": category_name,
                    "city": "Минск",
                    "category": category,
                },
            )
            profile.first_name = "Тест"
            profile.last_name = category_name
            profile.city = "Минск"
            profile.category = category
            profile.description = "Тестовая анкета."
            profile.career_start = date(2018, 6, 1)
            profile.save()
            for kind, amount in prices.items():
                field = CategoryPriceField.objects.filter(
                    category=category, kind=kind
                ).first()
                if field is None:
                    continue
                SpecialistPrice.objects.update_or_create(
                    specialist=profile,
                    price_field=field,
                    defaults={"amount": Decimal(amount)},
                )
            profiles[category_name] = profile
            self.stdout.write(f"{email} — Тест {category_name}")

        customer = self._customer()
        photographer = profiles.get("Фотограф")
        host = profiles.get("Ведущий")
        if customer and photographer and host:
            self._sample_project(customer, photographer, host)
        self.stdout.write(f"Пароль тестовых аккаунтов: {PASSWORD}")

    def _customer(self):
        email = "test.customer@fiesta.local"
        account, created = Account.objects.get_or_create(
            email=email,
            defaults={"role": Account.Role.CUSTOMER},
        )
        if not created and account.role != Account.Role.CUSTOMER:
            self.stdout.write(f"Почта занята: {email}")
            return None
        account.set_password(PASSWORD)
        account.save()
        profile, _ = UserProfile.objects.get_or_create(
            account=account,
            defaults={"first_name": "Тест", "last_name": "Пользователь", "city": "Минск"},
        )
        profile.first_name = "Тест"
        profile.last_name = "Пользователь"
        profile.city = "Минск"
        profile.save()
        self.stdout.write(f"{email} — Тест Пользователь")
        return profile

    def _sample_project(self, customer, photographer, host):
        event_type = EventType.objects.filter(name="Свадьба").first()
        if event_type is None:
            return
        project, _ = Project.objects.get_or_create(
            owner=customer,
            title="Тестовая свадьба",
            defaults={
                "event_type": event_type,
                "event_date": date(2026, 6, 1),
                "description": "Тестовый завершённый проект.",
                "status": Project.Status.COMPLETED,
            },
        )
        for role_title, specialist, rating in (
            ("Фотограф", photographer, 5),
            ("Ведущий", host, 3),
        ):
            RoleCandidate.objects.get_or_create(
                project=project,
                role_title=role_title,
                specialist=specialist,
                defaults={"category": specialist.category, "status": RoleCandidate.Status.SELECTED},
            )
            Review.objects.get_or_create(
                author=customer,
                specialist=specialist,
                project=project,
                defaults={"rating": rating, "text": "Тестовый отзыв."},
            )
