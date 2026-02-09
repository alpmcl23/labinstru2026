import streamlit as st
import requests
import time
import base64
import os


st.set_page_config(
    page_title="LabInstru – Dashboard Meteorológico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== OCULTA HEADER COMPLETAMENTE & SIDEBAR MAIS ESTREITA ==========
st.markdown("""
<style>
header {visibility: hidden;}
header {height: 0 !important;}
body {padding-top: 0 !important;}
/* Sidebar cinza: ainda mais estreita */
section[data-testid="stSidebar"] {
    min-width: 340px !important;
    max-width: 340px !important;
    width: 340px !important;
    padding-right: 10px !important;
}
div[data-testid="stSidebarContent"] {
    min-width: 322px !important;
    max-width: 322px !important;
    width: 322px !important;
}
div[data-testid="stRadio"] {
    min-width: 305px !important;
    max-width: 305px !important;
    width: 305px !important;
}
/* Label das opções do menu SEM quebra */
div[data-testid="stSidebar"] .stRadio label {
    font-size: 1.13em;
    white-space: nowrap !important;
    padding-left: 2px !important;
}
/* Nome do laboratório grande, preto, SEM QUEBRA, centralizado */
.titulo-labinst {
    font-size: 2em !important;
    color: #000 !important;
    font-weight: bold;
    text-align: center;
    margin-top: 0.22em;
    margin-bottom: 0.6em;
    line-height: 1.07;
    letter-spacing: 0.01em;
    font-family: 'Arial', sans-serif;
    white-space: nowrap !important;
}
@media (max-width: 700px) {
    .titulo-labinst { font-size: 1.15em !important;}
}
.bloco {background: #f8fbff; border-radius: 18px; padding: 28px 26px; box-shadow: 0 4px 24px #05445e22; margin-bottom: 22px;}
.bloco:hover {box-shadow: 0 8px 32px #189ab444;}
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ========== MENU E TÍTULOS ==========
#MENU_KEYS = [
 #   "Home", "Quem Somos", "Dashboard", "Rede de Estações HOBO", "Condições atuais da atmosfera",
  #  "Jogos Meteorológicos", "Estágio Curricular", "Projetos", "Eventos", "Contato"
#]





# ========== MENU E TÍTULOS ==========
MENU_KEYS = [
    "Home", "Quem Somos", "Dashboard", "Rede de Estações HOBO", "Condições atuais da atmosfera","Satélite e radar","Estágio Curricular", "Projetos", "Eventos", "Contato"
]





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

# ========== CONFIG GEMINI ==========
API_KEY = "AIzaSyDxNmGoseKwIogLqQNloLEEQv-whSnjy7Q"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def perguntar_gemini(pergunta):
    prompt = (
        "Você é ZEUS, um assistente especialista em Meteorologia do laboratório LabInstru. "
        "Responda de forma didática, curta e objetiva sobre meteorologia, climatologia, satélites e fenômenos ambientais. "
        "Sugira gráficos, mapas ou imagens quando for útil. "
        "Se a pergunta não for sobre meteorologia, explique educadamente que só responde perguntas meteorológicas.\n"
        f"Pergunta: {pergunta}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(API_URL, json=body, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "⚠️ Desculpe, não foi possível obter resposta agora."

# ========== SIDEBAR ==========
with st.sidebar:
    pagina = st.radio(
        "Menu",
        options=MENU_KEYS,
        format_func=lambda x: TITULOS[x],
        index=0
    )
    st.session_state.pagina = pagina

    # ========== NOVO CHAT ZEUS ==========
    # Estado do chat
    if "zeus_open_sb" not in st.session_state:
        st.session_state.zeus_open_sb = True
    if "zeus_hist_sb" not in st.session_state:
        st.session_state.zeus_hist_sb = [
            {"role": "assistant", "msg": "Olá! ⚡ Eu sou <b>ZEUS</b>, seu assistente meteorológico. Pergunte sobre previsão, mapas ou fenômenos climáticos!"}
        ]
    if "zeus_digitando_sb" not in st.session_state:
        st.session_state.zeus_digitando_sb = False

    # CSS do chat Zeus
    st.markdown("""
    <style>
    .zeus-sidebar-chat {margin-top: 18px;}
    #zeus-chat-panel {background: #f6f8fb; border-radius: 17px 17px 0 0; box-shadow: 0 4px 18px #1976d220;
        padding: 0; display: flex; flex-direction: column; height: 1px; min-width: 240px; width: 100%;
        overflow: hidden; border: 1.7px solid #d0e1f3;}
    .zeus-header {background: linear-gradient(90deg, #1976d2 80%, #56c6e6 100%); color: #fff;
        padding: 12px 13px 10px 10px; display: flex; align-items: center; gap: 11px; font-size: 1.09em;
        font-weight: 600; border-radius: 17px 17px 0 0;}
    .zeus-header img {width: 27px; height: 27px; border-radius: 50%; border: 2.2px solid #fff; object-fit: cover;}
    #zeus-mensagens-wrap {flex: 1; background: #f6f8fb; padding: 0; display: flex; flex-direction: column; min-height: 0;}
    #zeus-mensagens {flex: 1; overflow-y: auto; height: 260px; padding: 10px 6px 10px 10px; display: flex;
        flex-direction: column; gap: 8px; background: #f6f8fb; scroll-behavior: smooth; min-height: 0;}
    .zeus-balao-assistant {align-self: flex-start; background: linear-gradient(90deg,#c5e1fa 80%,#e1eaf5 100%);
        color: #17394a; margin: 1.5px 0; padding: 8px 13px; border-radius: 0 12px 12px 12px; font-size: 1em;
        max-width: 89%; box-shadow: 0 2px 8px #1976d214; word-break: break-word;}
    .zeus-balao-user {align-self: flex-end; background: linear-gradient(90deg,#b9f3c8 85%,#e7faec 100%);
        color: #135c1a; margin: 1.5px 0; padding: 8px 13px; border-radius: 12px 0 12px 12px; font-size: 1em;
        max-width: 89%; box-shadow: 0 2px 8px #1976d214; word-break: break-word;}
    .zeus-digitando {align-self: flex-start; background: #e7f4fd; color: #1461a0; padding: 7px 11px;
        border-radius: 0 12px 12px 12px; font-style: italic; font-size: 1em; max-width: 70%; margin-top: 1.5px; margin-bottom: 0.5px;}
    #zeus-input-bar {display: flex; gap: 8px; align-items: center; padding: 9px 10px 8px 8px;
        background: #f8fafc; border-top: 1.3px solid #d8e2ec;}
    #zeus-txt {flex: 1; padding: 7px 10px; border-radius: 8px; border: 1.3px solid #a6b9d2;
        font-size: 1em; outline: none; background: #fff;}
    #zeus-send-btn {background: linear-gradient(90deg,#36b05f 60%,#1976d2 100%); color: #fff; font-weight: bold;
        border: none; padding: 7px 13px; border-radius: 9px; cursor: pointer; font-size: 1em;
        transition: background .18s, box-shadow .18s;}
    #zeus-send-btn:active {background: linear-gradient(90deg,#229944 60%,#005cb2 100%);}
    #zeus-fechar-btn {background: none; border: none; color: #fff; font-size: 1.15em; cursor: pointer; margin-left: auto; opacity: .73; transition: opacity .18s;}
    #zeus-fechar-btn:hover { opacity:1; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="zeus-sidebar-chat">', unsafe_allow_html=True)
    if st.session_state.zeus_open_sb:
        st.markdown('<div id="zeus-chat-panel">', unsafe_allow_html=True)
        st.markdown("""
        <div class="zeus-header">
            <img src="https://raw.githubusercontent.com/Adrianolp01/trovao/main/ZEUS_logo_branco.jpg">
            Zeus
            <button id="zeus-fechar-btn" onclick="window.parent.postMessage({fecharZeus:true},'*')">✕</button>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div id="zeus-mensagens-wrap">', unsafe_allow_html=True)
        chat_html = '<div id="zeus-mensagens">'
        for m in st.session_state.zeus_hist_sb[-30:]:
            if m["role"] == "user":
                chat_html += f'<div class="zeus-balao-user">{m["msg"]}</div>'
            else:
                chat_html += f'<div class="zeus-balao-assistant">{m["msg"]}</div>'
        if st.session_state.zeus_digitando_sb:
            chat_html += '<div class="zeus-digitando">Digitando...</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # fim do wrap

        with st.form("zeus-chat-form", clear_on_submit=True):
            st.markdown('<div id="zeus-input-bar">', unsafe_allow_html=True)
            txt = st.text_input("", value="", key="zeus-txt", max_chars=350, placeholder="Pergunte sobre meteorologia...", label_visibility="collapsed")
            send = st.form_submit_button("Enviar")
            sair = st.form_submit_button("Sair do chat")
            st.markdown('</div>', unsafe_allow_html=True)
        if send and txt.strip():
            st.session_state.zeus_hist_sb.append({"role": "user", "msg": txt.strip()})
            st.session_state.zeus_digitando_sb = True
            st.rerun()
        if sair:
            st.session_state.zeus_open_sb = False
            st.rerun()
        if st.session_state.zeus_digitando_sb:
            with st.spinner("ZEUS está digitando..."):
                time.sleep(1.05)
                pergunta = [m["msg"] for m in reversed(st.session_state.zeus_hist_sb) if m["role"] == "user"][0]
                resposta = perguntar_gemini(pergunta)
                st.session_state.zeus_hist_sb.append({"role": "assistant", "msg": resposta})
                st.session_state.zeus_digitando_sb = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if st.button("Abrir ChatBot"):
            st.session_state.zeus_open_sb = True
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ========== CONTEÚDO PRINCIPAL ==========
pagina = st.session_state.get("pagina", "Home")

# =================== HOME ===================
if pagina == "Home":
    col1, col2, col3 = st.columns([1,4,1])
    with col2:
        st.image("labinst_logo.png", use_container_width=True)
        st.markdown(
            """
            <div class='titulo-labinst'>
                Laboratório de Instrumentação Meteorológica
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("""
    <div class="bloco">
        <div style="display: flex; align-items: center;">
            <div style="flex:2;">
                <h2 style="color:#111; margin-bottom:18px;">
                    Bem-vindo ao <span style="color:#111;">LabInstru</span> – EST/UEA
                </h2>
                <p style="font-size:1.15em; color:#222;">
                    O Laboratório de Instrumentação Meteorológica da EST/UEA, conhecido como <b>LabInstru</b>, foi criado para atender as demandas do Curso de Graduação em Meteorologia.<br><br>
                    Está localizado na sala C29, da Escola Superior de Tecnologia da UEA, na avenida Darcy Vargas, nº 1200. Encontra-se equipado com diversos sensores meteorológicos, utilizados durante as aulas práticas da disciplina Instrumentação Meteorológica, além de conjuntos de estações adquiridos através de projetos de pesquisa.<br><br>
                    Também dispomos de aparelhos como fontes de alimentação, estação de solda, GPS, além de ferramentas essenciais para o funcionamento, instalação e manutenção das estações meteorológicas.
                </p>
            </div>
            <div style="flex:1; text-align:center;">
                <img src="foto_laboratorio.jpg" width="340" style="border-radius:14px; margin-left:28px; box-shadow:0 2px 18px #0B3D9115;">
                <div style="font-size:.98em; color:#888; margin-top:8px;">Sala C29 – EST/UEA</div>
            </div>
        </div>
        <hr style="margin:30px 0 18px 0;">
        <h3 style="color:#145DA0;">Atividades do LabInstru:</h3>
        <ul style="font-size:1.09em; color:#222; line-height:1.6;">
            <li>Montagem e manutenção de equipamentos meteorológicos;</li>
            <li>Manter uma rede de Estações Meteorológicas em funcionamento contínuo em Manaus;</li>
            <li>Organizar os dados coletados nas estações instaladas pelo laboratório;</li>
            <li>Dar suporte a projetos de pesquisa para instalação e operação de instrumentos de monitoramento de variáveis atmosféricas;</li>
            <li>Disponibilizar dados para a população em geral, popularizando a Meteorologia;</li>
            <li>Realizar aulas práticas da disciplina Instrumentação Meteorológica, e, quando solicitado, para professores de outras disciplinas e/ou instituições;</li>
            <li>Desenvolver atividades de pesquisa e extensão;</li>
            <li>Receber alunos pré-concluintes para estágio curricular.</li>
        </ul>
        <h3 style="color:#145DA0;">Localização:</h3>

<p style="font-size:1.1em; color:#333;">
    Sala C29 – Escola Superior de Tecnologia (EST/UEA)<br>
    Avenida Darcy Vargas, nº 1200 – Manaus, AM
</p>

<iframe 
    src="https://www.openstreetmap.org/export/embed.html?bbox=-60.0179%2C-3.0919%2C-60.0171%2C-3.0913&layer=mapnik&marker=-3.0916%2C-60.0175"
    width="100%" height="320" frameborder="0"
    style="border-radius:12px; margin-top:10px;">
</iframe>

</div>
""", unsafe_allow_html=True)











elif pagina == "Rede de Estações HOBO":
    import pandas as pd
    import numpy as np
    import folium
    import json
    from streamlit_folium import st_folium
    from supabase import create_client
    import plotly.graph_objects as go
    import streamlit as st

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
    df_est = pd.DataFrame(dados)

    manaus_lat, manaus_lon = -3.05, -59.96
    mapa = folium.Map(location=[manaus_lat, manaus_lon], zoom_start=12, tiles="OpenStreetMap")

    geojson_path = "contorno_manaus.geojson"
    with open(geojson_path, "r", encoding="utf-8") as f:
        manaus_geo = json.load(f)

    folium.GeoJson(
        manaus_geo,
        name="Contorno de Manaus",
        style_function=lambda feature: {
            'fillColor': '#00000000',
            'color': '#000000',
            'weight': 4,
            'fillOpacity': 0.0
        },
        tooltip="Município de Manaus"
    ).add_to(mapa)

    for _, row in df_est.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(
                f"<b>{row['Nome']}</b><br>Zona: {row['Zona']}<br>Instalada: {row['Instalacao']}<br>Dias com dados: {row['Dias_dados']}",
                max_width=260
            ),
            tooltip=row["Nome"],
            icon=folium.Icon(color="Red", icon="info-sign")
        ).add_to(mapa)

    st_folium(mapa, width=1900, height=950)

    col1, col2, col3 = st.columns(3)
    with col1:
        variaveis = ["Precipitação", "Temperatura", "Umidade"]
        variavel = st.selectbox("Variável", variaveis, index=0)
    with col2:
        estacoes = df_est["Nome"].tolist()
        estacao = st.selectbox("Estação", estacoes, index=0)
    with col3:
        anos = list(range(2013, 2021))
        ano = st.selectbox("Ano", anos, index=0)

    SUPABASE_URL = "https://pcrywykqioyzetdzxjae.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjcnl3eWtxaW95emV0ZHp4amFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NjE1MjYsImV4cCI6MjA2NzAzNzUyNn0.1kDyYzMnnmaV3SyS3_GmIlBgvOkBFifjmHlBj67pjnE"
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    variavel_nome = (
        "chuva" if variavel == "Precipitação"
        else "temperatura" if variavel == "Temperatura"
        else "umidade" if variavel == "Umidade"
        else variavel.lower()
    )
    tabela_nome = f"ESTACAO_{estacao}_{variavel_nome}_{ano}"
    coluna_valor = (
        "chuva_mm" if variavel == "Precipitação"
        else "temperatura_c" if variavel == "Temperatura"
        else "umidade" if variavel == "Umidade"
        else "valor"
    )

    @st.cache_data
    def load_data(tabela_nome):
        try:
            res = supabase.table(tabela_nome).select("*").limit(10000).execute()
            df = pd.DataFrame(res.data)
            return df
        except Exception as e:
            st.error(f"Erro ao consultar a tabela: {e}")
            return pd.DataFrame()

    df = load_data(tabela_nome)

    if df.empty or coluna_valor not in df.columns:
        st.warning(
            f"Nenhum dado encontrado na tabela `{tabela_nome}` para a variável selecionada. 😢\n\n"
            f"Verifique se a tabela existe e se contém a coluna `{coluna_valor}`."
        )
    else:
        df['data'] = pd.to_datetime(df['data'])
        df['mes'] = df['data'].dt.month
        df['dia'] = df['data'].dt.day

        mat = np.full((12, 31), np.nan)
        for _, row in df.iterrows():
            m, d = int(row['mes']), int(row['dia'])
            if 1 <= m <= 12 and 1 <= d <= 31:
                mat[m-1, d-1] = row[coluna_valor]

        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
                 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        dias = list(range(1, 32))
        dias_por_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        df_hm = pd.DataFrame(mat, index=meses, columns=dias)

        if df[coluna_valor].dropna().empty:
            zmax = 1
        else:
            zmax = np.nanmax(df[coluna_valor])

        fig = go.Figure(data=go.Heatmap(
            z=df_hm.values,
            x=df_hm.columns,
            y=df_hm.index,
            colorscale='YlGnBu',
            zmin=0,
            zmax=zmax,
            colorbar=dict(title=f"{variavel}"),
            hoverongaps=False,
            showscale=True,
            zsmooth=False
        ))

        for i in range(df_hm.shape[0]):
            for j in range(df_hm.shape[1]):
                if j >= dias_por_mes[i] or np.isnan(df_hm.iloc[i, j]):
                    fig.add_shape(
                        type="rect",
                        x0=float(df_hm.columns[j]) - 0.5, x1=float(df_hm.columns[j]) + 0.5,
                        y0=i - 0.5, y1=i + 0.5,
                        fillcolor="lightgray", line=dict(width=0),
                        layer="above"
                    )

        fig.update_layout(
            title=f"Mapa de {variavel.lower()} diária em {estacao} — {ano}<br><sup>{variavel} diária, cinza = dias inexistentes/ausentes</sup>",
            xaxis_title="Dia",
            yaxis_title="",
            xaxis=dict(
                tickmode='array',
                tickvals=dias,
                ticktext=[str(d) for d in dias],
                tickangle=0,
            ),
            autosize=True,
            width=1100,
            height=650,
            margin=dict(l=80, r=30, t=90, b=40),
            font=dict(size=13)
        )

        st.plotly_chart(fig, use_container_width=True)



elif pagina == "Condições atuais da atmosfera":
    import streamlit as st
    import folium
    from streamlit_folium import st_folium
    from datetime import datetime, timedelta, timezone, date
    import pytz
    import requests
    import pandas as pd
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry
    from folium import FeatureGroup, LayerControl, DivIcon, IFrame, Popup
    import matplotlib.pyplot as plt
    from io import BytesIO
    import base64

    st.markdown("""
    <style>
    .labinstru-card {
        background: #f3fafe;
        border-radius: 16px;
        padding: 22px 28px 18px 28px;
        border: 1.5px solid #d6e7f7;
        margin-bottom: 18px;
        box-shadow: 0 2px 12px #05445e11;
    }
    .labinstru-card h2 {
        color: #145DA0;
        font-size: 1.55em;
        margin-bottom: 8px;
        font-weight: 800;
        letter-spacing: 0.01em;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <h1 style='color:#145DA0;'>☀️ Condições Atuais da Atmosfera – Manaus</h1>
    """, unsafe_allow_html=True)

    proxima = (datetime.now(pytz.timezone("America/Manaus")) + timedelta(minutes=10)).strftime('%H:%M')
    st.markdown(f"<span style='font-size: 0.95em; color: #888;'>⏳ Próxima atualização automática: {proxima} (em até 10 min)</span>", unsafe_allow_html=True)

    if st.button("🔄 Atualizar Agora"):
        st.cache_data.clear()
        st.experimental_rerun()

    LAT, LON = -3.11, -60.02
    DELTA = 0.5
    API_KEY = "D949FBD6-5C4D-11F0-81BE-42010A80001F"

    def fahrenheit_to_celsius_corrected(f):
        return (f - 32) * 5.0 / 9.0 - 8.0

    @st.cache_data(ttl=1800)
    def carregar_dados_virtual():
        hoje = date.today()
        inicio = hoje - timedelta(days=31)
        cache = requests_cache.CachedSession('.cache', expire_after=600)
        retry_session = retry(cache, retries=5, backoff_factor=0.2)
        client = openmeteo_requests.Client(session=retry_session)

        params = {
            "latitude": LAT,
            "longitude": LON,
            "hourly": ["pm2_5"],
            "start_date": str(inicio),
            "end_date": str(hoje),
            "timezone": "America/Manaus"
        }

        responses = client.weather_api("https://air-quality-api.open-meteo.com/v1/air-quality", params=params)
        response = responses[0]
        hourly = response.Hourly()
        pm2_5 = hourly.Variables(0).ValuesAsNumpy()
        tempo = pd.date_range(start=pd.to_datetime(hourly.Time(), unit="s"),
                              end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
                              freq=pd.Timedelta(seconds=hourly.Interval()),
                              inclusive="left")
        df = pd.DataFrame({"datetime": tempo, "pm2_5": pm2_5})
        df["hora"] = df["datetime"].dt.hour
        return df[df["hora"] == 15].copy()

    @st.cache_data(ttl=600)
    def carregar_purpleair_temp():
        url = (
            f"https://api.purpleair.com/v1/sensors"
            f"?fields=latitude,longitude,name,temperature_a,last_seen"
            f"&location_type=0"
            f"&nwlng={LON-DELTA}&nwlat={LAT+DELTA}&selng={LON+DELTA}&selat={LAT-DELTA}"
        )
        headers = {"X-API-Key": API_KEY}
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.status_code == 200 else None

    @st.cache_data(ttl=600)
    def carregar_purpleair_pm():
        url = (
            f"https://api.purpleair.com/v1/sensors"
            f"?fields=latitude,longitude,name,pm2.5_10minute,last_seen"
            f"&location_type=0"
            f"&nwlng={LON-DELTA}&nwlat={LAT+DELTA}&selng={LON+DELTA}&selat={LAT-DELTA}"
        )
        headers = {"X-API-Key": API_KEY}
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.status_code == 200 else None

    mapa_temp = folium.Map(location=[LAT, LON], zoom_start=12)
    dados_temp = carregar_purpleair_temp()
    if dados_temp and dados_temp.get("data"):
        campos = dados_temp["fields"]
        for row in dados_temp["data"]:
            s = dict(zip(campos, row))
            nome = s.get("name", "Sensor")
            lat, lon = s.get("latitude"), s.get("longitude")
            raw_temp = s.get("temperature_a")
            if raw_temp:
                temp = fahrenheit_to_celsius_corrected(float(raw_temp))
                hora = datetime.fromtimestamp(s.get("last_seen", 0), tz=timezone.utc).astimezone(pytz.timezone('America/Manaus')).strftime("%d/%m/%Y %H:%M:%S")
                popup = f"<b>{nome}</b><br>Temperatura: <b>{temp:.1f}°C</b><br>Atualizado: {hora}"
                folium.Marker(
                    location=[lat, lon],
                    popup=popup,
                    tooltip=nome,
                    icon=DivIcon(
                        icon_size=(45, 22),
                        icon_anchor=(22, 11),
                        html=f"""<div style='background-color:#33c2ff; color:#000; border-radius:6px;
                                padding:2px 8px; font-weight:bold; border:2px solid #222;
                                font-size:1.2em; text-align:center;'>{temp:.1f}°</div>"""
                    )
                ).add_to(mapa_temp)

    mapa_ar = folium.Map(location=[LAT, LON], zoom_start=12)
    virtual_layer = FeatureGroup(name="Qualidade do Ar – Estações Virtuais")
    df_15h = carregar_dados_virtual()

    if not df_15h.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        for y1, y2, cor in [(0, 25, "limegreen"), (25, 50, "yellow"), (50, 75, "orange"), (75, 125, "red"), (125, 160, "purple")]:
            ax.axhspan(y1, y2, color=cor, alpha=0.5)
        ax.bar(df_15h["datetime"].dt.strftime("%d/%m"), df_15h["pm2_5"], color='black')
        ax.set_title("PM2.5 às 15h – Open-Meteo")
        ax.set_xlabel("Dia")
        ax.set_ylabel("PM2.5 (µg/m³)")
        ax.set_ylim(0, 160)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        html_img = f'<img src="data:image/png;base64,{img_base64}" width="720">'
        popup = Popup(IFrame(html_img, width=740, height=420), max_width=750)
        media_pm = float(df_15h["pm2_5"].mean())
        cor_virtual = "limegreen" if media_pm <= 25 else "yellow" if media_pm <= 50 else "orange"
    else:
        popup = Popup("<b>Sem dados de PM2.5 às 15h.</b>", max_width=300)
        media_pm = 0.0
        cor_virtual = "gray"

    folium.Marker(
        location=[LAT, LON],
        popup=popup,
        tooltip="Clique para gráfico PM2.5",
        icon=DivIcon(
            icon_size=(45, 22),
            icon_anchor=(22, 11),
            html=f"""<div style='background-color:{cor_virtual}; color:#000; border-radius:6px;
                    padding:2px 8px; font-weight:bold; border:2px solid #222;
                    font-size:1.2em; text-align:center;'>{media_pm:.1f}</div>"""
        )
    ).add_to(virtual_layer)
    virtual_layer.add_to(mapa_ar)

    real_layer = FeatureGroup(name="Qualidade do Ar – Estações Reais")
    dados_pm = carregar_purpleair_pm()
    if dados_pm and dados_pm.get("data"):
        campos = dados_pm["fields"]
        for row in dados_pm["data"]:
            s = dict(zip(campos, row))
            nome = s.get("name", "Sensor")
            lat, lon = s.get("latitude"), s.get("longitude")
            pm = s.get("pm2.5_10minute")
            if pm is not None:
                def cor_pm25(v):
                    if v <= 12: return "#39e639"
                    elif v <= 35.4: return "#ffff00"
                    elif v <= 55.4: return "#ff9900"
                    elif v <= 150.4: return "#ff3333"
                    elif v <= 250.4: return "#a633cc"
                    else: return "#7e0023"
                cor = cor_pm25(pm)
                hora = datetime.fromtimestamp(s.get("last_seen", 0), tz=timezone.utc).astimezone(pytz.timezone("America/Manaus")).strftime("%d/%m/%Y %H:%M:%S")
                popup = f"<b>{nome}</b><br>PM2.5: <b>{float(pm):.1f}</b> µg/m³<br>Atualizado: {hora}"
                folium.Marker(
                    location=[lat, lon],
                    popup=popup,
                    tooltip=nome,
                    icon=DivIcon(
                        icon_size=(45, 22),
                        icon_anchor=(22, 11),
                        html=f"""<div style='background-color:{cor}; color:#000; border-radius:6px;
                                padding:2px 8px; font-weight:bold; border:2px solid #222;
                                font-size:1.2em; text-align:center;'>{float(pm):.1f}</div>"""
                    )
                ).add_to(real_layer)

    real_layer.add_to(mapa_ar)
    LayerControl(collapsed=False).add_to(mapa_ar)

    # ====== EXIBIÇÃO FINAL EM ESTILO "SATÉLITE E RADAR" ======
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class='labinstru-card'>
            <h2>M1 – Temperatura Real (PurpleAir)</h2>
            <div style='margin-top: 10px;'>
        """, unsafe_allow_html=True)
        st_folium(mapa_temp, width=1210, height=820)
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='labinstru-card'>
            <h2>M2 – Qualidade do Ar (Virtual e Real)</h2>
            <div style='margin-top: 10px;'>
        """, unsafe_allow_html=True)
        st_folium(mapa_ar, width=1210, height=820)
        st.markdown("</div></div>", unsafe_allow_html=True)




elif pagina == "Satélite e radar":
    import streamlit as st
    from datetime import datetime
    import pytz

    st.markdown("""
    <style>
    .labinstru-card {
        background: #f3fafe;
        border-radius: 16px;
        padding: 12px 18px 8px 18px;
        border: 1.5px solid #d6e7f7;
        margin-bottom: 20px;
        box-shadow: 0 2px 12px #05445e11;
        height: 740px;
    }
    .labinstru-card h2 {
        color: #145DA0;
        font-size: 1.2em;
        margin-bottom: 6px;
        font-weight: 800;
        letter-spacing: 0.01em;
        text-align: center;
    }
    .labinstru-status {
        display: block;
        background: #e63946;
        color: #fff;
        font-weight: bold;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.95em;
        box-shadow: 0 2px 4px #0002;
        text-align: center;
        margin-bottom: 6px;
    }
    iframe { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # ============================
    # LINHA 1: Radar e Satélite
    # ============================
    col1, col2 = st.columns(2)

    with col1:
        manaus_tz = pytz.timezone('America/Manaus')
        agora_manaus = datetime.now(manaus_tz)
        hora_formatada = agora_manaus.strftime('%d/%m/%Y %H:%M')

        st.markdown(f"""
        <div class='labinstru-card'>
            <h2>M1 – Radar Meteorológico (RainViewer)</h2>
            <div class="labinstru-status">Atualizado: {hora_formatada}</div>
            <iframe src="https://www.rainviewer.com/map.html?loc=lat:-3.12,lon:-60.02,zoom:9"
                    width="100%" height="640" frameborder="0"></iframe>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='labinstru-card'>
            <h2>M2 – Satélite GOES-19 (Canal 13)</h2>
            <div class="labinstru-status">Fonte: CPTEC/INPE</div>
            <iframe src="https://www.cptec.inpe.br/dsat/?product=ch13_noaa&product_opacity=6&zoom=5&x=3600.0000&y=2950.0000&animate=true&t=200.00&options=false&static=true"
                    width="100%" height="640" scrolling="no" frameborder="0"></iframe>
        </div>
        """, unsafe_allow_html=True)

    # ============================
    # LINHA 2: Câmera ao Vivo e meteoblue
    # ============================
    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"""
        <div class='labinstru-card'>
            <h2>M3 – Câmera ao Vivo (EST-UEA)</h2>
            <div class="labinstru-status">AO VIVO</div>
            <iframe src="https://rtsp.me/embed/KPbwo57M/" width="100%" height="640" allowfullscreen></iframe>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='labinstru-card'>
            <h2>M4 – Mapa Interativo (meteoblue)</h2>
            <div class="labinstru-status">Camadas meteorológicas</div>
            <iframe src="https://www.meteoblue.com/pt/tempo/mapas/widget/manaus_brasil_3663517?windAnimation=1&gust=1&satellite=1&cloudsAndPrecipitation=1&temperature=1&sunshine=1&extremeForecastIndex=1&geoloc=fixed&tempunit=C&windunit=km%252Fh&lengthunit=metric&zoom=5&autowidth=auto"
                    width="100%" height="640" frameborder="0" scrolling="no" allowtransparency="true"
                    sandbox="allow-same-origin allow-scripts allow-popups allow-popups-to-escape-sandbox">
            </iframe>
        </div>
        """, unsafe_allow_html=True)



elif pagina == "Jogos Meteorológicos":
    st.markdown("""
    <div class='bloco'>
        <h2 style='color:#145DA0; text-align:center; margin-bottom:18px;'>🎡 Roleta Meteorológica</h2>
    </div>
    """, unsafe_allow_html=True)

    roleta_html = """
    <div style="text-align: center; font-family: Arial, sans-serif; background: linear-gradient(#87ceeb, #fff); min-height: 100vh; padding: 0;">
    <h1 style="color:#005fa3;margin-top:20px;">🌦️ Roleta Meteorológica</h1>
    <div id="wheel-container" style="position:relative;width:520px;height:520px;margin:20px auto;">
      <div id="pointer" style="position:absolute;top:-20px;left:50%;transform:translateX(-50%);width:40px;height:40px;background:gold;clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);z-index:10;box-shadow:0 0 5px #333;"></div>
      <div id="wheel" style="position:absolute;top:0;left:0;width:520px;height:520px;border-radius:50%;overflow:hidden;border:10px solid #444;box-shadow:0 0 10px #555;">
        <div id="segments" style="width:100%;height:100%;transform-origin:center;transition:transform 2s ease-out;"></div>
      </div>
    </div>
    <button onclick="spin()" id="botao-girar" style="margin-top:20px;padding:12px 28px;font-size:18px;cursor:pointer;border-radius:7px;background:#0077cc;color:white;border:none;">🎲 Girar</button>
    <div id="pergunta" style="margin-top:30px;font-size:1.2em;color:#333;max-width:520px;margin-left:auto;margin-right:auto;word-break:break-word;white-space:normal;"></div>
    <div id="alternativas" style="width:100%;max-width:520px;margin:0 auto;box-sizing:border-box;"></div>
    <div id="feedback" style="margin-top:18px;font-weight:bold;font-size:1.2em;"></div>
    <div id="resultado-final" style="margin-top:22px;font-size:1.4em;color:darkblue;font-weight:bold;"></div>

    <script>
    const outcomes = [
      {
        evento: "🌞 Dia ensolarado",
        pergunta: "Qual gás mais contribui para o efeito estufa natural?",
        alternativas: ["Dióxido de carbono", "Metano", "Vapor d'água", "Ozônio"],
        correta: "Vapor d'água"
      },
      {
        evento: "🌧️ Chuva forte",
        pergunta: "Que instrumento mede a quantidade de chuva?",
        alternativas: ["Barômetro", "Pluviômetro", "Anemômetro", "Termômetro"],
        correta: "Pluviômetro"
      },
      {
        evento: "🌪️ Tornado!",
        pergunta: "Os tornados geralmente ocorrem em qual tipo de nuvem?",
        alternativas: ["Cirros", "Cumulus", "Estratos", "Cumulonimbus"],
        correta: "Cumulonimbus"
      },
      {
        evento: "❄️ Neve intensa",
        pergunta: "Qual estado físico da água forma a neve?",
        alternativas: ["Gasoso", "Líquido", "Sólido", "Plasma"],
        correta: "Sólido"
      },
      {
        evento: "🌈 Arco-íris no céu",
        pergunta: "O arco-íris é causado por qual fenômeno da luz?",
        alternativas: ["Reflexão", "Difração", "Polarização", "Refração"],
        correta: "Refração"
      },
      {
        evento: "💨 Ventania",
        pergunta: "Que instrumento mede a velocidade do vento?",
        alternativas: ["Barômetro", "Pluviômetro", "Anemômetro", "Higrômetro"],
        correta: "Anemômetro"
      },
      {
        evento: "☁️ Céu nublado",
        pergunta: "Qual é a principal composição das nuvens?",
        alternativas: ["Gelo seco", "Gotículas de água", "Vapor de carbono", "Ozônio"],
        correta: "Gotículas de água"
      },
      {
        evento: "⛈️ Tempestade elétrica",
        pergunta: "O que provoca os raios?",
        alternativas: ["Atrito de nuvens", "Movimento do vento", "Descarga elétrica", "Refração da luz"],
        correta: "Descarga elétrica"
      }
    ];

    const cores = ["#f7dc6f", "#85c1e9", "#d98880", "#a9cce3", "#82e0aa", "#f5b041", "#d7bde2", "#f1948a"];
    const segments = document.getElementById("segments");
    const segAngle = 360 / outcomes.length;

    outcomes.forEach((o, i) => {
      const div = document.createElement("div");
      div.className = "segment";
      div.style.position = "absolute";
      div.style.width = "50%";
      div.style.height = "50%";
      div.style.left = "50%";
      div.style.top = "50%";
      div.style.transformOrigin = "0% 0%";
      div.style.background = cores[i % cores.length];
      div.style.color = "#333";
      div.style.fontSize = "18px";
      div.style.display = "flex";
      div.style.alignItems = "center";
      div.style.justifyContent = "center";
      div.style.transform = `rotate(${i * segAngle}deg) skewY(${90 - segAngle}deg)`;
      div.innerHTML = `<div style="transform: skewY(${-(90 - segAngle)}deg) rotate(${segAngle/2}deg); text-align:center; width:180px; padding:3px;">${o.evento}</div>`;
      segments.appendChild(div);
    });

    let acertos = 0;
    let rodadas = 0;
    const rodadasTotais = 5;

    function spin() {
      document.getElementById("pergunta").textContent = "";
      document.getElementById("alternativas").innerHTML = "";
      document.getElementById("feedback").textContent = "";
      document.getElementById("resultado-final").textContent = "";

      const rnd = Math.floor(Math.random() * outcomes.length);
      const rotation = (360 * 5) + (360 - rnd * segAngle - segAngle/2);
      segments.style.transition = "transform 2s ease-out";
      segments.style.transform = `rotate(${rotation}deg)`;

      setTimeout(() => {
        mostrarPergunta(rnd);
      }, 2200);
    }

    function mostrarPergunta(indice) {
      const o = outcomes[indice];
      document.getElementById("pergunta").textContent = `📝 ${o.evento}: ${o.pergunta}`;
      const altDiv = document.getElementById("alternativas");
      altDiv.innerHTML = "";
      o.alternativas.forEach(alt => {
        const btn = document.createElement("div");
        btn.textContent = alt;
        btn.className = "alternativa";
        btn.style.display = "block";
        btn.style.margin = "8px auto";
        btn.style.padding = "12px 16px";
        btn.style.width = "98%";
        btn.style.maxWidth = "480px";
        btn.style.boxSizing = "border-box";
        btn.style.cursor = "pointer";
        btn.style.background = "#eee";
        btn.style.border = "1px solid #ccc";
        btn.style.borderRadius = "4px";
        btn.style.wordBreak = "break-word";
        btn.style.whiteSpace = "normal";
        btn.style.fontSize = "1.08em";
        btn.onmouseover = function(){btn.style.background="#ddd"};
        btn.onmouseout = function(){btn.style.background="#eee"};
        btn.onclick = () => verificarResposta(alt, o.correta);
        altDiv.appendChild(btn);
      });
    }

    function verificarResposta(resposta, correta) {
      if (resposta === correta) {
        document.getElementById("feedback").textContent = "🎉 Resposta correta!";
        document.getElementById("feedback").style.color = "green";
        acertos++;
      } else {
        document.getElementById("feedback").textContent = `❌ Errado. Resposta correta: ${correta}`;
        document.getElementById("feedback").style.color = "red";
      }

      rodadas++;

      if (rodadas >= rodadasTotais) {
        setTimeout(() => {
          avaliarDesempenho();
        }, 1500);
      }
    }

    function avaliarDesempenho() {
      const resultado = document.getElementById("resultado-final");
      const botao = document.getElementById("botao-girar");
      botao.disabled = true;

      if (acertos >= 3) {
        resultado.textContent = `🌟 Bom trabalho! Você acertou ${acertos} de ${rodadasTotais}.`;
        resultado.style.color = "green";
      } else {
        resultado.textContent = `😕 Precisa melhorar. Você acertou apenas ${acertos} de ${rodadasTotais}.`;
        resultado.style.color = "red";
      }
    }
    </script>
    """

    import streamlit.components.v1 as components
    components.html(roleta_html, height=1300)











elif pagina == "Estágio Curricular":
    st.markdown('<div class="bloco"><h2>📄 Estágio curricular</h2></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#f3f8fd;padding:18px 16px;border-radius:13px;box-shadow:0 1px 14px #1976d216;margin:18px 0;">
    O Labinstru oferece oportunidade de estágio (não remunerado) para alunos do curso de Meteorologia da UEA, regularmente matriculados na disciplina Estágio Supervisionado.<br><br>
    Alunos de outras instituições também podem participar.<br><br>
    Interessados entrar em contato: <b>mloliveira@uea.edu.br</b>
    </div>
    """, unsafe_allow_html=True)

    estagiarios = [
        ("Rodrigo da Cruz França", "Graduação em Meteorologia (UEA)", "Instrumentação Meteorológica", "13/04/2016 a 30/08/2016"),
        ("Daniela Correa Chaves", "Engenharia Ambiental (Fametro)", "Instrumentação Meteorológica", "11/09/2017 a 15/11/2017"),
        ("Katharina de Carvalho Capobiango", "Graduação em Meteorologia (UEA)", "Instrumentação Meteorológica", "21/03/2019 a 28/06/2019"),
        ("Lemoel Pimentel de Brito", "Graduação em Meteorologia (UEA)", "Instrumentação Meteorológica", "06/12/2022 a 15/08/2023"),
        ("Sarah Regina Oliveira de Sousa", "Graduação em Meteorologia (UEA)", "Instrumentação Meteorológica", "01/02/2024 a 19/07/2024"),
        ("Nigia Núbia Santos Silva", "Graduação em Meteorologia (UEA)", "Instrumentação Meteorológica", "19/05/2025 a atual"),
    ]

    for i in range(0, len(estagiarios), 3):
        cols = st.columns(3)
        for j, (nome, curso, area, periodo) in enumerate(estagiarios[i:i+3]):
            with cols[j]:
                st.markdown(
                    f"""
                    <div style="background:#fff; border-radius:11px; box-shadow:0 1px 10px #1976d214; padding:16px; margin:12px; text-align:left;">
                        <strong>{nome}</strong><br>
                        <span style="font-size:0.98em;">Curso: {curso}</span><br>
                        <span style="font-size:0.98em;">Área: {area}</span><br>
                        <span style="font-size:0.98em;">Período: {periodo}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )





# =================== EQUIPE ===================
elif pagina == "Quem Somos":
    import base64
    st.markdown('<div class="bloco"><h2>👥 Equipe do Projeto</h2></div>', unsafe_allow_html=True)

    nomes = [
        ("maria_betania.jpg", "Profa. Maria Betânia Leal", "Pesquisadora/Responsável", "http://lattes.cnpq.br/6645179913028377"),
        ("rodrigo_souza.jpg", "Prof. Rodrigo Souza", "Pesquisador", "http://lattes.cnpq.br/5622102962091766"),
        ("rita_valeria.jpg", "Profa. Rita Valéria Andreoli", "Pesquisadora", "http://lattes.cnpq.br/5550289805439528"),
        ("adriano_pedrosa.jpg", "Adriano Pedrosa", "Bolsista PROTLAB-TRAINEE", "http://lattes.cnpq.br/6377229544645237"),
        ("lemoel_pimentel.jpg", "Lemoel Pimentel", "Voluntário", "http://lattes.cnpq.br/5593010828707685"),
        ("tales_lopes.jpg", "Tales Lopes", "Bolsista IC/CNPq", "http://lattes.cnpq.br/4700126765072371"),
        ("nigia_nubia.jpg", "Nigia Núbia", "Estagiária", "http://lattes.cnpq.br/4303038702531746"),
        ("abraao_soares.jpg", "Abraão Soares", "Voluntário", "http://lattes.cnpq.br/0216316050483380"),
    ]

    for i in range(0, len(nomes), 3):  # Três colunas por linha
        cols = st.columns(3)
        for j, (img, nome, cargo, lattes) in enumerate(nomes[i:i+3]):
            with cols[j]:
                # Carrega e codifica imagem em base64
                with open(img, "rb") as f:
                    img_bytes = f.read()
                img_base64 = base64.b64encode(img_bytes).decode()

                # Bloco completo com foto grande e centralizada
                st.markdown(f"""
                    <div style="background:#f3f8fd;padding:25px;border-radius:14px;
                                box-shadow:0 2px 18px #1976d216;margin:20px;text-align:center;
                                display: flex; flex-direction: column; align-items: center;">
                        <div style="width: 250px; height: 250px; overflow: hidden; border-radius: 50%; margin-bottom: 15px;">
                            <img src="data:image/jpeg;base64,{img_base64}"
                                 style="width: 100%; height: 100%; object-fit: cover;" />
                        </div>
                        <div style="line-height: 1.5;">
                            <div style="font-weight: bold; font-size: 1.15em;">{nome}</div>
                            <div style="font-size: 1em; color: #666;">{cargo}</div>
                            <div style="margin-top: 8px;">
                                <a href="{lattes}" target="_blank" style="font-size: 0.95em;">Currículo</a>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)


# =================== PROJETOS ===================

elif pagina == "Projetos":

    # INICIAÇÃO CIENTÍFICA (LISTA COMPLETA)
    st.markdown('<div class="bloco"><h2>📁 PROJETOS</h2></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="bloco"><h3>INICIAÇÃO CIENTÍFICA</h3></div>', unsafe_allow_html=True)
    st.markdown("""
    <ol style="font-size:1.07em; color:#222; padding-left:22px;">
        <li>RAFAEL RODRIGUES BATISTA. EVENTOS EXTREMOS DE CHUVA EM MANAUS: UMA CARACTERIZAÇÃO COM BASE EM DADOS OBSERVACIONAIS. 2023. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>DAYANNE CÁSSIA PEREIRA DE OLIVEIRA. CONFORTO TÉRMICO EM MANAUS: UM ESTUDO OBSERVACIONAL. 2023. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>SELTON GERMANO DOS SANTOS BANDERA. VARIABILIDADE ESPAÇO-TEMPORAL DO ÍNDICE DE CONFORTO TÉRMICO EM MANAUS E SUA RELAÇÃO COM O TIPO DE COBERTURA DO SOLO. 2019. INICIAÇÃO CIENTÍFICA. UNIVERSIDADE DO ESTADO DO AMAZONAS, UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>MARCELO VICTOR GONCALVES SIMAS. ANÁLISE DA PRECIPITAÇÃO DIÁRIA DE MANAUS E SUA RELAÇÃO COM A OCORRÊNCIA DE EL NIÑO, LA NIÑA E ANOS NEUTROS. 2018. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>SELTON GERMANO DOS SANTOS BANDEIRA. ESTUDO DAS CARACTERÍSTICAS FÍSICAS DAS GOTAS DE CHUVA REGISTRADAS EM MANAUS ATRAVÉS DE DADOS DE DISDRÔMETROS. 2018. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>ANDRÉ LUIZ LETURIONDO SEGUNDO. ANÁLISE DA PRECIPITAÇÃO NA BACIA DO MINDÚ E SUA RELAÇÃO COM O NÍVEL DA ÁGUA ATINGINDO PELO IGARAPÉ NA ZONA CENTRO-SUL DE MANAUS. 2018. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO A PESQUISA DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>GABRIEL FRASÃO DE ANDRADE ROJAS. MÉTODOS COMPUTACIONAIS PARA PROCESSAMENTO DE DADOS METEOROLÓGICOS. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>FÁBIO DOS SANTOS SOUZA. SISTEMA DE INFORMAÇÃO PARA UMA REDE DE ESTAÇÕES METEOROLÓGICAS E ANÁLISE DE DADOS DE PRECIPITAÇÃO COM REDES NEURAIS ARTIFICIAIS. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM ENGENHARIA DE COMPUTAÇÃO) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>EMANUEL OLIVEIRA DA SILVA. UTILIZAÇÃO DE APRENDIZAGEM DE MÁQUINA PARA CLASSIFICAÇÃO DE PRECIPITAÇÕES. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM ENGENHARIA DE COMPUTAÇÃO) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>NICOLI PINHEIRO DE ARAÚJO. UTILIZAÇÃO DE REDES NEURAIS PARA PREVISÃO DE PRECIPITAÇÃO EM MANAUS, AMAZONAS. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM ENGENHARIA DE COMPUTAÇÃO) - UNIVERSIDADE DO ESTADO DO AMAZONAS, CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>LEMOEL PIMENTEL DE BRITO. RELAÇÃO ENTRE AS RAJADAS DE VENTO E A OCORRÊNCIA DE NUVENS ESTRATIFORMES E CONVECTIVAS EM MANAUS. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>RANYLLI CARLA DA FIQUEIREDO. ASSOCIAÇÃO ENTRE VARIÁVEIS METEOROLÓGICAS E INCIDÊNCIA DE DOENÇAS RELACIONADAS AO VETOR AEDES AEGYPTI NA CIDADE DE MANAUS. 2017. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>LEMOEL PIMENTEL DE BRITO.CARACTERIZAÇÃO DO REGIME DE VENTO À SUPERFÍCIE EM MANAUS. 2016. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>SÉRGIO ALEXANDRE DA SILVA. ANÁLISE DOS ÍNDICES DE CALOR EM DIFERENTES BAIRROS DE MANAUS. 2016. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>ANDRÉ LUIZ LETURIONDO SEGUNDO. DISTRIBUIÇÃO ESPACIAL DA PRECIPITAÇÃO EM MANAUS E SUA RELAÇÃO COM O NÍVEL DOS IGARAPÉS DO QUARENTA E DO MINDÚ - PARTE II. 2016. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>JANDERSON DO NASCIMENTO LIRA. PREVISÃO DA COTA DO RIO NEGRO UTILIZANDO REDES NEURAIS ARTIFICIAIS. 2016. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM ENGENHARIA DE COMPUTAÇÃO) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO A PESQUISA DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>ANDRÉ LUIZ LETURIONDO SEGUNDO. DISTRIBUIÇÃO ESPACIAL DA PRECIPITAÇÃO EM MANAUS E SUA RELAÇÃO COM O NÍVEL DOS IGARAPÉS DO QUARENTA E DO MINDÚ. 2015. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>IGOR BRUNO CARRAMANHO DE AZEVEDO. ANÁLISE DAS CONDIÇÕES METEOROLÓGICAS NAS CAPITAIS DO BRASIL PARA ESTUDO DO ÍNDICE DE CALOR EM MANAUS -PARTE II. 2015. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO A PESQUISA DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>IGOR BRUNO CARRAMANHO DE AZEVEDO. ANÁLISE DAS CONDIÇÕES METEOROLÓGICAS NAS CAPITAIS DO BRASIL PARA ESTUDO DO ÍNDICE DE CALOR EM MANAUS. 2014. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO A PESQUISA DO ESTADO DO AMAZONAS. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>PRISCILA PEREIRA DE MIRANDA. RELAÇÃO ENTRE OS EVENTOS DE PRECIPITAÇÃO, NÍVEL DE IGARAPÉ E DANOS CAUSADOS À POPULAÇÃO DE MANAUS. 2014. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>RAFAEL GOMES BARBOSA. GOTAS DE CHUVA - PARTE I. 2013. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>PRISCILA PEREIRA DE MIRANDA. ANÁLISE DA DISTRIBUIÇÃO DA PRECIPITAÇÃO NA BACIA AMAZÔNICA 2 PARTE II. 2013. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>NIKOLAI DA SILVA ESPONIZA. ANÁLISE DAS OBSERVAÇÕES REALIZADAS NA ESTAÇÃO METEOROLÓGICA NA ESCOLA SUPERIOR DE TECNOLOGIA 2 PARTE II. 2013. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>LADY LAYANA MARTINS CUSTÓDIO. ILHAS DE CALOR URBANO E CAMPOS METEOROLÓGICOS EM MANAUS. 2012. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>RAFAEL GOMES BARBOSA. GOTAS DE CHUVA. 2012. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>NIKOLAI DA SILVA ESPINOZA. ANÁLISE DAS OBSERVAÇÕES REALIZADAS NA ESTAÇÃO METEOROLÓGICA NA ESCOLA SUPERIOR DE TECNOLOGIA. 2012. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>PRISCILA PEREIRA DE MIRANDA. ANÁLISE DA DISTRIBUIÇÃO DA PRECIPITAÇÃO NA BACIA AMAZÔNICA. 2012. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>LADY LAYANA MARTINS CUSTÓDIO. ESTUDO DA VARIABILIDADE ESPACIAL E TEMPORAL DAS VARIÁVEIS METEOROLÓGICAS EM ESTAÇÕES CLIMÁTICAS DA CIDADE DE MANAUS. 2011. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>NIKOLAI DA SILVA ESPINOZA. MONITORAMENTO DO TEMPO E DO CLIMA ATRAVÉS DE OBSERVAÇÕES METEOROLÓGICAS REALIZADAS NA ESCOLA SUPERIOR DE TECNOLOGIA. 2011. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA..</li>
        <li>RAFAEL GOMES BARBOSA. PINGOS DE CHUVA. 2011. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISAS DA AMAZÔNIA. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>YARA FERNANDA SILVA DE OLIVEIRA. ANÁLISE DAS VARIÁVEIS METEOROLÓGICAS EM ESTAÇÕES CLIMÁTICAS DA CIDADE DE MANAUS. 2010. INICIAÇÃO CIENTÍFICA. (GRADUANDA EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISA DO ESTADO DO AMAZONAS. ORIENTADORA: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>
        <li>ANE FERREIRA SIQUARA. MONITORAMENTO DE DADOS METEOROLÓGICOS EM ESTAÇÃO METEOROLÓGICA AUTOMÁTICA NO CAMPUS DA EST. 2010. INICIAÇÃO CIENTÍFICA. (GRADUANDO EM METEOROLOGIA) - UNIVERSIDADE DO ESTADO DO AMAZONAS, FUNDAÇÃO DE AMPARO À PESQUISAS DA AMAZÔNIA. ORIENTADOR: MARIA BETÂNIA LEAL DE OLIVEIRA.</li>



    </ol>
    """, unsafe_allow_html=True)

   
    # PROJETOS DE EXTENSÃO
    
    st.markdown('<div class="bloco"><h3>PROJETOS DE EXTENSÃO</h3></div>', unsafe_allow_html=True)
    projetos_extensao = [
        ("2014–2015", "MENINAS DO TEMPO. CHAMADA PÚBLICA Nº 18/2013 MCTI/CNPQ/SPM-PR/PETROBRAS – MENINAS E JOVENS FAZENDO CIÊNCIAS EXATAS, ENGENHARIAS E COMPUTAÇÃO. FINANCIADOR(ES): CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO–CNPQ."),
        ("2017–2018", "CURUMINS DO TEMPO. EDITAL Nº 38/2017–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PROGEX/UEA)."),
        ("2018–2019", "DE OLHO NA CHUVA. PROJETO DE EXTENSÃO SUBMETIDO E APROVADO NO EDITAL Nº 40/2018–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PROGEX/UEA)."),
        ("2018–2019", "CURUMINS DO TEMPO – FASE II. PROJETO DE EXTENSÃO SUBMETIDO E APROVADO NO EDITAL Nº 40/2018–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PROGEX/UEA)."),
        ("2018–2021", "MENINAS E A CIÊNCIA ATMOSFÉRICA. PROPOSTA SUBMETIDA E APROVADA NA CHAMADA CNPQ/MCTIC Nº 31/2018 – MENINAS NAS CIÊNCIAS EXATAS, ENGENHARIAS E COMPUTAÇÃO. FINANCIADOR(ES): CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO–CNPQ."),
        ("2022–2023", "EM DIA COM A METEOROLOGIA. EDITAL Nº 57/2022–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PADEX/UEA)."),
        ("2023–2024", "EM DIA COM A METEOROLOGIA – FASE 2. EDITAL Nº 73/2023–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PADEX/UEA). WEBSITE: HTTPS://EMDIACOMAMETEOROLOGIAAMY.CANVA.SITE/"),
        ("2024–2025", "EM DIA COM A METEOROLOGIA – FASE 3. EDITAL Nº 50/2024–GR/UEA, DO PROGRAMA INSTITUCIONAL DE EXTENSÃO, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PROGEX/UEA). WEBSITE: HTTPS://EMDIACOMAMETEOROLOGIAAMY.CANVA.SITE/"),
    ]
    for ano, desc in projetos_extensao:
        st.markdown(
            f"""
            <div style="background:#fff; border-radius:11px; box-shadow:0 1px 10px #1976d214; padding:16px; margin:12px 0 0 0; text-align:left;">
                <strong>{ano}</strong><br>
                {desc}
            </div>
            """,
            unsafe_allow_html=True
        )

    # PROJETOS PARA REALIZAÇÃO DE EVENTOS
    st.markdown('<div class="bloco"><h3>PROJETOS PARA REALIZAÇÃO DE EVENTOS</h3></div>', unsafe_allow_html=True)
    projetos_eventos = [
        ("2024", "IV SEMANA ACADÊMICA DE METEOROLOGIA DA UEA. EDITAL Nº 56/2023 DO PROGRAMA DE APOIO AO DESENVOLVIMENTO DE EVENTOS, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PADEV/UEA)."),
        ("2025", "POPULARIZANDO A METEOROLOGIA PARA TODOS. EDITAL Nº 66/2024 DO PROGRAMA DE APOIO AO DESENVOLVIMENTO DE EVENTOS, DA UNIVERSIDADE DO ESTADO DO AMAZONAS (PADEV/UEA)."),
    ]
    for ano, desc in projetos_eventos:
        st.markdown(
            f"""
            <div style="background:#fff; border-radius:11px; box-shadow:0 1px 10px #1976d214; padding:16px; margin:12px 0 0 0; text-align:left;">
                <strong>{ano}</strong><br>
                {desc}
            </div>
            """,
            unsafe_allow_html=True
        )

    # PROJETOS VINCULADOS
    st.markdown('<div class="bloco"><h3>PROJETOS VINCULADOS</h3></div>', unsafe_allow_html=True)
    projetos_vinculados = [
        ("2023–ATUAL", "O EFEITO DA VARIABILIDADE CLIMÁTICA MULTIESCALAR NA PRECIPITAÇÃO SOBRE A AMÉRICA DO SUL E SUAS RELAÇÕES COM EXTREMOS DE CHEIAS, SECAS E AS QUEIMADAS NA AMAZÔNIA. EDITAL N. 001/2023 – UNIVERSAL – FAPEAM 20 ANOS. COORDENADOR(A): RITA VALÉRIA ANDREOLI DE SOUZA. COORDENADOR: RODRIGO AUGUSTO FERREIRA DE SOUZA."),
        ("2021–ATUAL", "QUALIDADE DO AR DA AMAZÔNIA: UM PROGRAMA EDUCACIONAL SOBRE A POLUIÇÃO DO AR. CUOMO FOUNDATION."),
        ("2020–2024", "SISTEMA DE PREVISÃO DE SECAS E ENCHENTES EM APOIO À GESTÃO DA RESERVA DE DESENVOLVIMENTO SUSTENTÁVEL DO RIO MADEIRA. CHAMADA PÚBLICA N. 001/2020 – FAPESP/FAPEAM. COORDENADOR: FRANCIS WAGNER DA SILVA CORREA."),
        ("2014–2019", "PREVISÃO DE TEMPO DE CURTO PRAZO EM ULTRA-ALTA RESOLUÇÃO ESPACIAL PARA A REGIÃO METROPOLITANA DE MANAUS: IMPACTO DO REFINAMENTO DA CONDIÇÃO INICIAL DA ATMOSFERA COM ASSIMILAÇÃO DE DADOS DE LOCAIS. CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTÍFICO E TECNOLÓGICO. COORDENADORES: RITA VALÉRIA ANDREOLI DE SOUZA."),
        ("2010–2019", "REDE DE MUDANÇAS CLIMÁTICAS DA AMAZÔNIA – REMCLAM. FINANCIADOR DE ESTUDOS E PROJETOS-FINEP. COORDENADORA: RITA VALÉRIA ANDREOLI DE SOUZA."),
        ("2013–2017", "PROINFRA/FINEP: MONTAGEM DE SITE EXPERIMENTAL PARA PESQUISA EM ÁREAS MULTIDISCIPLINARES DAS CIÊNCIAS FÍSICAS, QUÍMICAS E BIOLÓGICAS. FINANCIADORA DE ESTUDOS E PROJETOS-FINEP. COORDENADORA: RITA VALÉRIA ANDREOLI DE SOUZA."),
        ("2007–2011", "REDE DE METEOROLOGIA E HIDROLOGIA DO ESTADO DO AMAZONAS – REMETH. CHAMADA PÚBLICA MCT/FINEP/CT-INFRA PROINFRA 01/2006. COORDENADOR: JORG JOHANNES OHLY."),
    ]
    for ano, desc in projetos_vinculados:
        st.markdown(
            f"""
            <div style="background:#fff; border-radius:11px; box-shadow:0 1px 10px #1976d214; padding:16px; margin:12px 0 0 0; text-align:left;">
                <strong>{ano}</strong><br>
                {desc}
            </div>
            """,
            unsafe_allow_html=True
        )


















elif pagina == "Contato":
    st.markdown("""
    <div class='bloco'>
        <h2 style='color:#145DA0;'>Contato</h2>
        <div style='text-align:center; font-size:1.15em; margin-bottom:20px;'>
            📧 <a href="mailto:mloliveira@uea.edu.br">mloliveira@uea.edu.br</a>
        </div>
        <div style="margin:32px 0 20px 0; text-align:left; font-size:1.10em; color:#222;">
            <b>Interessados em conhecer o LabInstru e projetos associados podem agendar sua visita pelo e-mail acima, informando:</b>
            <ul style="font-size:1.05em; line-height:1.7; margin-left:18px;">
                <li>Nome da instituição de ensino</li>
                <li>Curso ou nível de ensino</li>
                <li>Número de alunos para a visita</li>
                <li>Objetivo da visita</li>
            </ul>
            O retorno será enviado com a confirmação e orientações para o agendamento.
        </div>
        <hr style="margin:28px 0 20px 0;">
        <div style="background:#f8fbff; border-radius:14px; box-shadow:0 2px 12px #189ab433; text-align:center; padding:18px 0; margin-bottom:12px;">
            <span style="font-size:1.13em; color:#145DA0; font-weight:bold; letter-spacing:1px;">
                Siga-nos também nas redes sociais:
            </span><br><br>
            <a href="https://www.instagram.com/lab.instru/" target="_blank" style="text-decoration:none;">
                <img src="https://cdn-icons-png.flaticon.com/512/1384/1384063.png" width="32" style="vertical-align:middle; margin-right:10px;">Instagram
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)






