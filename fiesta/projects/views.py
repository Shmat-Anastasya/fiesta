from catalog.views import render_page


def favorites(request):
    return render_page(request, "Избранное", "Это страница избранного.")


def projects(request):
    tabs = [
        ("all", "Все"),
        ("in_progress", "В процессе"),
        ("completed", "Завершённые"),
    ]
    current = request.GET.get("tab", "all")
    if current not in {code for code, title in tabs}:
        current = "all"
    current_title = dict(tabs)[current]
    return render_page(
        request,
        "Проекты",
        f"Это страница проектов. Открыта вкладка «{current_title}».",
        tabs=[
            {
                "code": code,
                "title": title,
                "active": code == current,
            }
            for code, title in tabs
        ],
        links=[
            {"url_name": "project_page", "title": "Страница проекта"},
            {"url_name": "review_page", "title": "Отзыв"},
            {"url_name": "review_reply", "title": "Ответ специалиста на отзыв"},
        ],
    )


def project_page(request):
    return render_page(
        request,
        "Проект",
        "Это страница проекта. На роль выбирается один специалист.",
    )


def review_page(request):
    return render_page(
        request,
        "Отзыв",
        "Это страница отзыва после завершения проекта.",
    )


def review_reply(request):
    return render_page(
        request,
        "Ответ на отзыв",
        "Это страница ответа специалиста на отзыв.",
    )
