from django.shortcuts import render
from datetime import datetime
import pytz
import folium
import json
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent

TITULOS = {
    "Home": "Pagina inicial",
    "Quem Somos": "Quem somos",
    "Dashboard": "Estação meteorologica da EST",
    "Rede de Estações HOBO": "Rede de estações HOBO",
    "Condições atuais da atmosfera": "O tempo agora",
    "Satélite e radar": "Satélite e radar",
    "Estágio Curricular": "Estágio Curricular",
    "Projetos": "Projetos",
    "Eventos": "Eventos",
    "Contato": "Contato"
}

def render_pagina(request, pagina):
    titulo = TITULOS.get(pagina, "Página")

    # Corrigir nome do template
    if pagina == "Rede de Estações HOBO":
        template = "siteapp/rede_de_estacoes_hobo.html"
    else:
        template = f"siteapp/{pagina.lower().replace(' ', '_')}.html"

    contexto = {"titulo": titulo}

    if pagina == "Rede de Estações HOBO":
        dados = [
            {"Nome": "EST", "Latitude": -3.09240, "Longitude": -60.01657, "Zona": "Centro-Sul", "Instalacao": "nov/12", "Dias_dados": 2610},
            {"Nome": "POL", "Latitude": -3.11980, "Longitude": -60.00724, "Zona": "Sul", "Instalacao": "abr/13", "Dias_dados": 1531},
            {"Nome": "IFAM", "Latitude": -3.07949, "Longitude": -59.93270, "Zona": "Leste", "Instalacao": "jun/13", "Dias_dados": 1459},
            {"Nome": "CMM", "Latitude": -3.13076, "Longitude": -60.02702, "Zona": "Sul", "Instalacao": "jul/13", "Dias_dados": 2059},
            {"Nome": "MUSA", "Latitude": -3.00337, "Longitude": -59.93967, "Zona": "Norte", "Instalacao": "ago/13", "Dias_dados": 1121},
            {"Nome": "INPA", "Latitude": -3.09690, "Longitude": -59.98276, "Zona": "Sul", "Instalacao": "out/13", "Dias_dados": 675},
            {"Nome": "PONTE", "Latitude": -3.11038, "Longitude": -60.06713, "Zona": "Oeste", "Instalacao": "abr/16", "Dias_dados": 858},
            {"Nome": "BOM", "Latitude": -3.20000, "Longitude": -60.00000, "Zona": "Sul", "Instalacao": "dez/17", "Dias_dados": 630},
            {"Nome": "EMB", "Latitude": -2.88753, "Longitude": -59.96852, "Zona": "Manaus", "Instalacao": "jun/13", "Dias_dados": 1621},
            {"Nome": "CALD", "Latitude": -3.26038, "Longitude": -60.22738, "Zona": "Iranduba", "Instalacao": "set/13", "Dias_dados": 2327}
        ]
        df = pd.DataFrame(dados)

        variaveis = ["Precipitação", "Temperatura", "Umidade"]
        estacoes = df["Nome"].tolist()
        anos = list(range(2013, 2021))

        variavel = request.GET.get("variavel", variaveis[0])
        nome_variavel_mapeada = {
            "Precipitação": "chuva",
            "Temperatura": "temperatura",
            "Umidade": "umidade"
        }.get(variavel, variavel.lower())

        nome_coluna = {
            "chuva": "chuva_mm",
            "temperatura": "temperatura_c",
            "umidade": "umidade"
        }.get(nome_variavel_mapeada, "valor")

        estacao = request.GET.get("estacao", estacoes[0])
        ano = int(request.GET.get("ano", anos[0]))

        mapa = folium.Map(location=[-3.05, -59.96], zoom_start=11, tiles="CartoDB positron")

        geo_path = base_dir / "siteapp/static/siteapp/geo/contorno_manaus.geojson"
        with open(geo_path, "r", encoding="utf-8") as f:
            manaus_geo = json.load(f)

        folium.GeoJson(
            manaus_geo,
            style_function=lambda feature: {
                'fillColor': '#00000000',
                'color': '#000000',
                'weight': 4,
                'fillOpacity': 0.0
            },
            tooltip="Município de Manaus"
        ).add_to(mapa)

        for _, row in df.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(
                    f"<b>{row['Nome']}</b><br>Zona: {row['Zona']}<br>Instalada: {row['Instalacao']}<br>Dias com dados: {row['Dias_dados']}",
                    max_width=260
                ),
                tooltip=row["Nome"],
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(mapa)

        contexto["mapa"] = mapa._repr_html_()
        contexto.update({
            "variaveis": variaveis,
            "estacoes": estacoes,
            "anos": anos,
            "variavel": variavel,
            "estacao": estacao,
            "ano": ano
        })

        SUPABASE_URL = "https://pcrywykqioyzetdzxjae.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjcnl3eWtxaW95emV0ZHp4amFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NjE1MjYsImV4cCI6MjA2NzAzNzUyNn0.1kDyYzMnnmaV3SyS3_GmIlBgvOkBFifjmHlBj67pjnE"
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        nome_tab = f"ESTACAO_{estacao}_{nome_variavel_mapeada}_{ano}"
        col_valor = nome_coluna

        try:
            dados_sup = supabase.table(nome_tab).select("*").limit(10000).execute().data
            df2 = pd.DataFrame(dados_sup)
            if df2.empty or col_valor not in df2.columns:
                contexto["erro"] = f"Nenhum dado encontrado na tabela `{nome_tab}` com a coluna `{col_valor}`."
            else:
                df2['data'] = pd.to_datetime(df2['data'])
                df2['mes'] = df2['data'].dt.month
                df2['dia'] = df2['data'].dt.day

                mat = np.full((12, 31), np.nan)
                for _, row in df2.iterrows():
                    m, d = int(row['mes']), int(row['dia'])
                    if 1 <= m <= 12 and 1 <= d <= 31:
                        mat[m-1, d-1] = row[col_valor]

                meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
                dias = list(range(1, 32))
                dias_mes = [31,28,31,30,31,30,31,31,30,31,30,31]
                df_hm = pd.DataFrame(mat, index=meses, columns=dias)

                fig = go.Figure(data=go.Heatmap(
                    z=df_hm.values, x=df_hm.columns, y=df_hm.index,
                    colorscale='YlGnBu', zmin=0, zmax=np.nanmax(df_hm.values),
                    colorbar=dict(title=variavel), hoverongaps=False
                ))

                for i in range(df_hm.shape[0]):
                    for j in range(df_hm.shape[1]):
                        if j >= dias_mes[i] or np.isnan(df_hm.iloc[i, j]):
                            fig.add_shape(
                                type="rect", x0=j+0.5, x1=j+1.5, y0=i-0.5, y1=i+0.5,
                                fillcolor="lightgray", line=dict(width=0), layer="above"
                            )

                fig.update_layout(
                    title=f"{variavel} diária em {estacao} – {ano}",
                    width=1100, height=650, margin=dict(l=80, r=30, t=90, b=40),
                )

                contexto["grafico"] = fig.to_html(full_html=False)
        except Exception as e:
            contexto["erro"] = f"Erro ao consultar Supabase: {e}"

    return render(request, template, contexto)
