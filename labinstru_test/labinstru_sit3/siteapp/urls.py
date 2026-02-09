from django.urls import path
from . import views

urlpatterns = [
    path('', lambda r: views.render_pagina(r, "Home"), name="home"),
    path('quem-somos/', lambda r: views.render_pagina(r, "Quem Somos"), name="quem_somos"),
    path('dashboard/', lambda r: views.render_pagina(r, "Dashboard"), name="dashboard"),
    path('rede-estacoes/', lambda r: views.render_pagina(r, "Rede de Estações HOBO"), name="rede"),
    path('condicoes/', lambda r: views.render_pagina(r, "Condições atuais da atmosfera"), name="condicoes"),
    path('satelite/', lambda r: views.render_pagina(r, "Satélite e radar"), name="satelite"),
    path('estagio/', lambda r: views.render_pagina(r, "Estágio Curricular"), name="estagio"),
    path('projetos/', lambda r: views.render_pagina(r, "Projetos"), name="projetos"),
    path('eventos/', lambda r: views.render_pagina(r, "Eventos"), name="eventos"),
    path('contato/', lambda r: views.render_pagina(r, "Contato"), name="contato"),
]
