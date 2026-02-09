from django.contrib import admin
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.utils.translation import gettext_lazy as _

# Endpoints que NÃO precisam de tradução (sem prefixo de idioma)
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # endpoint do set_language
    path("api/", include("siteapp.api_urls")),        # API do ZEUS e outras APIs
]

# Páginas do site COM tradução (com prefixo /pt/, /en/, /es/)
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("siteapp.urls")),                # inclui as rotas de páginas
)



