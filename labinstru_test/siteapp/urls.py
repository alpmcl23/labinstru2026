from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("quem-somos/", views.quem_somos, name="quem_somos"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("rede-estacoes-hobo/", views.rede_hobo, name="rede_hobo"),
    path("condicoes-atuais/", views.condicoes_atmosfera, name="condicoes"),
    path("satelite-e-radar/", views.satelite_radar, name="satelite_radar"),
    path("estagio-curricular/", views.estagio, name="estagio"),
    path("projetos/", views.projetos, name="projetos"),
    path("eventos/", views.eventos, name="eventos"),
    path("contato/", views.contato, name="contato"),
    path("app-labinstru/", views.app_labinstru, name="app_labinstru"),
    path("inmet/<str:station>/painel/", views.inmet_painel, name="inmet_painel"),

    # << rota única para mapas gerados >>
    path("embed/maps/<str:filename>", views.embed_map, name="embed_map"),
    path("produtos/agrometeorologia/", views.agrometeorologia, name="agrometeorologia"),
     path("energia-solar/", views.energia_solar, name="energia_solar"),
    path("produtos/construcao-civil/", views.construcao_civil, name="construcao_civil"),
    path("produtos/educacao-ambiental/", views.educacao_ambiental, name="educacao_ambiental"),
]
