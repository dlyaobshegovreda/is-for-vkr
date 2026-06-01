from django.conf import settings


def workshop_info(request):
    """Прокидывает реквизиты автосервиса во все шаблоны."""
    return {"workshop": getattr(settings, "WORKSHOP_INFO", {})}
