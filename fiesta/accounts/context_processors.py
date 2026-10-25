from catalog.models import Category

FOOTER_LABELS = {
    "Площадка": "Площадки",
    "Организатор": "Организаторы",
    "Ведущий": "Ведущие",
    "Музыкант": "Музыканты",
    "Диджей": "Диджеи",
    "Видеограф": "Видеографы",
    "Фотограф": "Фотографы",
    "Хореограф": "Хореографы",
    "Шоу-программа": "Шоу-программа",
    "Аниматор": "Аниматоры",
    "Стилист": "Стилисты",
    "Визажист": "Визажисты",
    "Декоратор": "Декораторы",
    "Кондитер": "Кондитеры",
    "Кейтеринг": "Кейтеринг",
}


def cabinet(request):
    name = ""
    if request.user.is_authenticated:
        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            profile = getattr(request.user, "specialist_profile", None)
        if profile is not None:
            name = profile.first_name or profile.last_name
        if not name:
            name = request.user.email
    categories = list(Category.objects.filter(is_hidden=False))
    by_name = {category.name: category for category in categories}
    footer_names = [
        "Площадка",
        "Ведущий",
        "Фотограф",
        "Видеограф",
        "Декоратор",
    ]
    return {
        "cabinet_name": name,
        "menu_categories": categories,
        "footer_categories": [
            {"pk": by_name[item].pk, "label": FOOTER_LABELS[item]}
            for item in footer_names
            if item in by_name
        ],
    }
