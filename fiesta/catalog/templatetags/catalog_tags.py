from django import template

register = template.Library()


@register.filter
def ru_reviews(count):
    count = int(count or 0)
    rest = abs(count) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "отзывов"
    elif last == 1:
        word = "отзыв"
    elif 2 <= last <= 4:
        word = "отзыва"
    else:
        word = "отзывов"
    return f"({count} {word})"
