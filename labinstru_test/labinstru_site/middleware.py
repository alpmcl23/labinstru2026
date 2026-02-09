# labinstru_site/middleware.py
from django.utils import translation
from django.conf import settings

class DefaultLanguageMiddleware:
    """
    Na primeira visita à raiz (sem prefixo e sem cookie de idioma),
    ativa PT-BR e grava o cookie para as próximas navegações.
    Impede que o Accept-Language do navegador troque para ES/EN.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang_cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")
        chosen = request.COOKIES.get(lang_cookie_name, "")
        path = request.path_info or "/"

        skip_prefixes = ("/en/", "/es/", "/pt/", "/pt-br/", "/admin/", "/i18n/", "/api/")
        has_prefix = path.startswith(skip_prefixes)

        # Sem cookie + sem prefixo -> força pt-br nesta resposta
        if not chosen and not has_prefix:
            translation.activate("pt-br")
            request.LANGUAGE_CODE = "pt-br"

        response = self.get_response(request)

        # Grava o cookie para persistir a escolha
        if not chosen and not has_prefix:
            max_age = getattr(settings, "LANGUAGE_COOKIE_AGE", 60 * 60 * 24 * 365)
            response.set_cookie(
                lang_cookie_name,
                "pt-br",
                max_age=max_age,
                samesite="Lax",
            )

        return response
