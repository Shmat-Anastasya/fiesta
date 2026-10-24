from django.shortcuts import render


def render_page(request, title, text, **extra):
    context = {"page_title": title, "page_text": text}
    context.update(extra)
    return render(request, "stub.html", context)


def home(request):
    return render_page(request, "Главная", "Это главная страница.")


def catalog(request):
    return render_page(
        request,
        "Каталог",
        "Это страница каталога. Здесь будут фильтр по стоимости за услугу или за час и сортировка по рейтингу или цене.",
        links=[
            {"url_name": "specialist_page", "title": "Страница специалиста"},
        ],
    )


def specialist_page(request):
    return render_page(request, "Страница специалиста", "Это страница специалиста.")


def questionnaire(request):
    return render_page(
        request,
        "Анкета",
        "Это короткая анкета: категория, описание, дата начала карьеры, главные фото и цены «от».",
    )


def portfolio(request):
    return render_page(request, "Портфолио", "Это страница портфолио.")
