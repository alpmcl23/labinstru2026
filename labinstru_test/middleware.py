# labinstru_site/middleware.py
from django.utils import translation
from django.conf import settings

class DefaultLanguageMiddleware:
    """
    Força pt-br na raiz (/) quando NÃO há cookie de idioma e
    a URL não tem prefixo (/en/, /es/, /pt-br/). Assim a primeira
    renderização já sai em português, independentemente do
    Accept-Language do navegador.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang_cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")
        chosen = request.COOKIES.get(lang_cookie_name, "")
        path = request.path_info or "/"

        # URLs que não queremos interceptar
        skip_prefixes = ("/en/", "/es/", "/pt/", "/pt-br/", "/admin/", "/i18n/", "/api/")
        has_prefix = path.startswith(skip_prefixes)

        # Se não há cookie e não há prefixo de linguagem na URL → ativa pt-br
        if not chosen and not has_prefix:
            translation.activate("pt-br")
            request.LANGUAGE_CODE = "pt-br"

        response = self.get_response(request)

        # Grava o cookie pt-br para as próximas navegações
        if not chosen and not has_prefix:
            max_age = getattr(settings, "LANGUAGE_COOKIE_AGE", 60 * 60 * 24 * 365)
            response.set_cookie(
                lang_cookie_name,
                "pt-br",
                max_age=max_age,
                samesite="Lax",
            )

        return response
