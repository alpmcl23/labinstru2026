# -*- coding: utf-8 -*-
"""
siteapp/views.py — versão consolidada
- Home / Quem somos / Dashboard / Projetos / Eventos / Estágio
- Rede de Estações HOBO (mapa + heatmap de precipitação via Supabase)
- Painel INMET (tempo real, diário, semanal, mensal, climatologia, alertas)
- Condições da Atmosfera + mapas Folium (Temperatura, PM2.5, Estações Virtuais)
- Satélite & Radar (comparador) usando iframes
- Embed de mapas em /embed/maps/<arquivo>.html (xframe liberado)
- Contato (envio por Gmail com senha de app)
- ZEUS (Assistente IA com filtro de escopo + Google CSE + Gemini)
"""

from __future__ import annotations

# =========================
# Imports padrão / utilitários
# =========================
import os
import re
import io
import json
import socket
import logging
import calendar
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, List
from urllib.parse import urlparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================
# Imports de terceiros
# =========================
import requests
import numpy as np
import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
from folium import Map, Marker, TileLayer
from folium.features import DivIcon
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from branca.element import MacroElement, Element, Template as BrancaTemplate
from jinja2 import Template as JinjaTemplate

try:
    from supabase import create_client  # pip install supabase
except Exception:
    create_client = None  # continua sem supabase

# =========================
# Imports Django
# =========================
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import (
    JsonResponse, Http404, FileResponse
)
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils._os import safe_join
from django.core.cache import cache
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection, BadHeaderError

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÕES / CONSTANTES
# =============================================================================
TZ = "America/Manaus"
TZ_AM = ZoneInfo(TZ)

# Supabase — pode sobrescrever via settings ou env
SUPABASE_URL = getattr(settings, "SUPABASE_URL", os.environ.get("SUPABASE_URL",
                   "https://pcrywykqioyzetdzxjae.supabase.co"))
SUPABASE_KEY = getattr(settings, "SUPABASE_KEY", os.environ.get("SUPABASE_KEY",
                   "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjcnl3eWtxaW95emV0ZHp4amFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NjE1MjYsImV4cCI6MjA2NzAzNzUyNn0.1kDyYzMnnmaV3SyS3_GmIlBgvOkBFifjmHlBj67pjnE"))

# PurpleAir
PURPLEAIR_API_KEY = getattr(settings, "PURPLEAIR_API_KEY",
                            "06D80FBA-AF5F-11F0-BDE5-4201AC1DC121")

# Gmail (contato)
SENDER_NAME  = "LabInstru"
SENDER_EMAIL = getattr(settings, "CONTACT_FROM_EMAIL", "alp.mcl23@uea.edu.br")
GMAIL_APP_PASSWORD = getattr(settings, "GMAIL_APP_PASSWORD", "oybyxdorpmtsqehf")
TO_EMAIL     = getattr(settings, "CONTACT_TO_EMAIL", "mloliveira@uea.edu.br")
FROM_EMAIL_FMT = f"{SENDER_NAME} <{SENDER_EMAIL}>"
TO_LIST = [TO_EMAIL]

# Painel INMET
INMET_TOKEN = getattr(settings, "INMET_TOKEN",
    "OVVKV3hMSjVWWGtVYm5wMGFsaVc1VXhteEYwY1cwSDI=9UJWxLJ5VXkUbnp0aliW5UxmxF0cW0H2")

HARDCODED_COORDS = {
    "A101": (-3.1030, -60.0250),  # Manaus
}

# Caminhos de mídia para mapas Folium (gerados)
MEDIA_MAPS_DIR  = os.path.join(settings.MEDIA_ROOT, "maps")
MEDIA_CACHE_DIR = os.path.join(settings.MEDIA_ROOT, "cache")
os.makedirs(MEDIA_MAPS_DIR,  exist_ok=True)
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

# =============================================================================
# PÁGINAS SIMPLES
# =============================================================================
def home(request):
    return render(request, "siteapp/home.html")

def dashboard(request):
    return render(request, "siteapp/dashboard.html")

def projetos(request):
    return render(request, "siteapp/projetos.html")

def eventos(request):
    return render(request, "siteapp/eventos.html")

def estagio(request):
    estagiarios = [
        {"nome": "Rodrigo da Cruz França", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "13/04/2016 a 30/08/2016"},
        {"nome": "Dania Correa Chaves", "curso": "Engenharia Ambiental (Fametro)", "area": "Instrumentação Meteorológica", "periodo": "11/09/2017 a 15/11/2017"},
        {"nome": "Katharina de Carvalho Capobiango", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "21/03/2019 a 28/06/2019"},
        {"nome": "Lemoel Pimentel de Brito", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "06/12/2022 a 15/08/2023"},
        {"nome": "Sarah Regina Oliveira de Sousa", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "01/02/2024 a 19/07/2024"},
        {"nome": "Nigia Núbia Santos Silva", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "19/05/2025 a atual"},
    ]
    for e in estagiarios:
        e["atual"] = "atual" in e["periodo"].lower()
    return render(request, "siteapp/estagio.html", {"estagiarios": estagiarios})

def quem_somos(request):
    equipe = [
        {"img": "equipe/maria_betania.jpg", "nome": "Profa. Maria Betânia Leal", "cargo": "Pesquisadora/Responsável", "lattes": "http://lattes.cnpq.br/6645179913028377"},
        {"img": "equipe/rodrigo_souza.jpg", "nome": "Prof. Rodrigo Souza", "cargo": "Pesquisador", "lattes": "http://lattes.cnpq.br/5622102962091766"},
        {"img": "equipe/rita_valeria.jpg", "nome": "Profa. Rita Valéria Andreoli", "cargo": "Pesquisadora", "lattes": "http://lattes.cnpq.br/5550289805439528"},
        {"img": "equipe/adriano_pedrosa.jpg", "nome": "Adriano Pedrosa", "cargo": "Bolsista PROTLAB-TRAINEE", "lattes": "http://lattes.cnpq.br/6377229544645237"},
        {"img": "equipe/lemoel_pimentel.jpg", "nome": "Lemoel Pimentel", "cargo": "Voluntário", "lattes": "http://lattes.cnpq.br/5593010828707685"},
        {"img": "equipe/abraao_soares.jpg", "nome": "Abraão Soares", "cargo": "Voluntário", "lattes": "http://lattes.cnpq.br/0216316050483380"},
    ]
    return render(request, "siteapp/quem_somos.html", {"equipe": equipe})

# =============================================================================
# REDE DE ESTAÇÕES HOBO (mapa + heatmap precipitação via Supabase)
# =============================================================================

def _iter_coords(obj):
    """Itera coords genéricos de um GeoJSON (lon,lat) -> (lat,lon)."""
    if isinstance(obj, dict):
        t = obj.get("type")
        if t == "FeatureCollection":
            for f in obj.get("features", []):
                yield from _iter_coords(f.get("geometry"))
        elif t == "Feature":
            yield from _iter_coords(obj.get("geometry"))
        else:
            yield from _iter_coords(obj.get("coordinates"))
    elif isinstance(obj, (list, tuple)):
        if len(obj) == 2 and all(isinstance(x, (int, float)) for x in obj):
            yield obj[1], obj[0]
        else:
            for el in obj:
                yield from _iter_coords(el)

def rede_hobo(request):
    # --- Estações (fixo) ---
    dados = [
        {"Nome": "EST",   "Latitude": -3.09240, "Longitude": -60.01657, "Zona": "Centro-Sul", "Instalacao": "nov/12", "Dias_dados": 2610},
        {"Nome": "POL",   "Latitude": -3.11980, "Longitude": -60.00724, "Zona": "Sul",        "Instalacao": "abr/13", "Dias_dados": 1531},
        {"Nome": "IFAM",  "Latitude": -3.07949, "Longitude": -59.93270, "Zona": "Leste",      "Instalacao": "jun/13", "Dias_dados": 1459},
        {"Nome": "CMM",   "Latitude": -3.13076, "Longitude": -60.02702, "Zona": "Sul",        "Instalacao": "jul/13", "Dias_dados": 2059},
        {"Nome": "MUSA",  "Latitude": -3.00337, "Longitude": -59.93967, "Zona": "Norte",      "Instalacao": "ago/13", "Dias_dados": 1121},
        {"Nome": "INPA",  "Latitude": -3.09690, "Longitude": -59.98276, "Zona": "Sul",        "Instalacao": "out/13", "Dias_dados": 675},
        {"Nome": "PONTE", "Latitude": -3.11038, "Longitude": -60.06713, "Zona": "Oeste",      "Instalacao": "abr/16", "Dias_dados": 858},
        {"Nome": "BOM",   "Latitude": -3.20000, "Longitude": -60.00000, "Zona": "Sul",        "Instalacao": "dez/17", "Dias_dados": 630},
        {"Nome": "EMB",   "Latitude": -2.88753, "Longitude": -59.96852, "Zona": "Manaus",     "Instalacao": "jun/13", "Dias_dados": 1621},
        {"Nome": "CALD",  "Latitude": -3.26038, "Longitude": -60.22738, "Zona": "Iranduba",   "Instalacao": "set/13", "Dias_dados": 2327},
    ]
    df_est = pd.DataFrame(dados)

    label_por_estacao = {
        "EST": "EST",
        "POL": "Policlínica",
        "IFAM": "IFAM",
        "CMM": "CMM",
        "MUSA": "MUSA",
        "INPA": "INPA",
        "PONTE": "Ponte Rio Negro",
        "BOM": "Bombeiros",
        "EMB": "EMBRAPA",
        "CALD": "Caldeirão (Iranduba)",
    }
    estacoes = [r["Nome"] for r in dados]
    opcoes_estacoes = [{"cod": cod, "label": label_por_estacao.get(cod, cod)} for cod in estacoes]

    variaveis = ["Precipitação"]
    variavel = request.GET.get("variavel", "Precipitação")
    estacao = request.GET.get("estacao", estacoes[0])
    try:
        ano = int(request.GET.get("ano", "2013"))
    except ValueError:
        ano = 2013

    escala = request.GET.get("escala", "max").lower()
    if escala not in {"max", "p99"}:
        escala = "max"

    # --- Mapa Folium (travado) ---
    manaus_lat, manaus_lon = -3.05, -59.96
    mapa = folium.Map(
        location=[manaus_lat, manaus_lon],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=False,
    )

    # contorno de Manaus
    geojson_path = os.path.join(settings.BASE_DIR, "static", "geo", "contorno_manaus.geojson")
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            manaus_geo = json.load(f)
        folium.GeoJson(
            manaus_geo, name="Contorno de Manaus",
            style_function=lambda _: {"fillColor": "#0000", "color": "#145DA0", "weight": 3, "fillOpacity": 0.0},
            tooltip="Município de Manaus", show=True
        ).add_to(mapa)
    except Exception:
        manaus_geo = None

    # marcadores de estações
    for _, r in df_est.iterrows():
        nome_legivel = label_por_estacao.get(r["Nome"], r["Nome"])
        html = (f"<div style='font-size:14px'><b>{nome_legivel}</b><br>"
                f"Zona: {r['Zona']}<br>Instalação: {r['Instalacao']}<br>"
                f"Dias com dados: {r['Dias_dados']}</div>")
        folium.Marker(
            [r["Latitude"], r["Longitude"]],
            tooltip=nome_legivel,
            popup=folium.Popup(html, max_width=280),
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(mapa)

    # enquadra tudo
    lats, lons = df_est["Latitude"].tolist(), df_est["Longitude"].tolist()
    if manaus_geo:
        for lat, lon in _iter_coords(manaus_geo):
            lats.append(lat); lons.append(lon)
    if lats and lons:
        try:
            mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20, 20))
        except Exception:
            pass

    # trava interações
    lock_tpl = BrancaTemplate("""
    {% macro script(this, kwargs) %}
      var map = {{this._parent.get_name()}};
      map.dragging.disable();
      map.scrollWheelZoom.disable();
      map.doubleClickZoom.disable();
      map.touchZoom.disable();
      map.boxZoom.disable();
      map.keyboard.disable();
    {% endmacro %}
    """)
    mlock = MacroElement(); mlock._template = lock_tpl
    mapa.add_child(mlock)
    mapa_html = mapa._repr_html_()

    # --- Supabase -> tabela chuva ---
    grafico_html = "<div class='alert alert-warning'>Sem dados.</div>"
    if create_client is None:
        grafico_html = "<div class='alert alert-warning'>Biblioteca Supabase não instalada.</div>"
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        slug_por_estacao = {
            "EST": "EST", "POL": "POL", "IFAM": "IFAM", "CMM": "CMM",
            "MUSA": "MUSA", "INPA": "INPA", "PONTE": "PONTE",
            "BOM": "BOMBEIROS", "EMB": "EMB", "CALD": "CALD",
        }
        estacao_slug = slug_por_estacao.get(estacao, estacao)
        base = f"ESTACAO_{estacao_slug}_chuva_{ano}"
        candidatos = [base, base.lower(), base.upper(), f"estacao_{estacao_slug.lower()}_chuva_{ano}"]

        df, tabela_ok, logs = pd.DataFrame(), None, []
        for nome in candidatos:
            try:
                res = supabase.table(nome).select("*").limit(100000).execute()
                tmp = pd.DataFrame(res.data or [])
                if not tmp.empty:
                    df, tabela_ok = tmp, nome; break
                logs.append(f"{nome}: vazia")
            except Exception as e:
                logs.append(f"{nome}: {e}")

        if df.empty or "data" not in df.columns:
            grafico_html = (
                f"<div class='alert alert-warning'>Não encontrei dados de precipitação para "
                f"<b>{label_por_estacao.get(estacao, estacao)}</b> / <b>{ano}</b>."
                f"<br><small>{' | '.join(logs)}</small></div>"
            )
        else:
            col_val = "chuva_mm" if "chuva_mm" in df.columns else \
                      "precipitacao_mm" if "precipitacao_mm" in df.columns else \
                      "mm" if "mm" in df.columns else "valor"
            if col_val not in df.columns:
                grafico_html = f"<div class='alert alert-warning'>Tabela <b>{tabela_ok}</b> sem coluna de valores.</div>"
            else:
                df["data"] = pd.to_datetime(df["data"], errors="coerce")
                df = df.dropna(subset=["data"])
                df["mes"] = df["data"].dt.month
                df["dia"] = df["data"].dt.day
                mat = np.full((12, 31), np.nan)
                for _, r in df.iterrows():
                    m, d = int(r["mes"]), int(r["dia"])
                    if 1 <= m <= 12 and 1 <= d <= 31:
                        val = pd.to_numeric(r[col_val], errors="coerce")
                        mat[m - 1, d - 1] = float(val) if pd.notna(val) else np.nan
                meses = ['janeiro','fevereiro','março','abril','maio','junho',
                         'julho','agosto','setembro','outubro','novembro','dezembro']
                dias = list(range(1, 32))
                df_hm = pd.DataFrame(mat, index=meses, columns=dias)

                serie = pd.to_numeric(df[col_val], errors="coerce")
                serie_valid = serie[serie.notna() & np.isfinite(serie)]
                vmin = 0.0
                if not serie_valid.empty:
                    vmax = float(np.nanpercentile(serie_valid, 99)) if escala == "p99" else float(np.nanmax(serie_valid))
                else:
                    vmax = 1.0
                if not np.isfinite(vmax) or vmax <= vmin:
                    vmax = vmin + 1e-6

                texto = np.empty_like(mat, dtype=object)
                for _, r in df.iterrows():
                    m, d = int(r["mes"]), int(r["dia"])
                    if 1 <= m <= 12 and 1 <= d <= 31:
                        val = pd.to_numeric(r[col_val], errors="coerce")
                        if pd.notna(val):
                            texto[m - 1, d - 1] = f"{d:02d}/{m:02d}/{ano} – {float(val):.2f} mm"
                        else:
                            texto[m - 1, d - 1] = "Sem dado"

                fig = go.Figure(data=go.Heatmap(
                    z=df_hm.values, x=df_hm.columns, y=df_hm.index,
                    text=texto, hoverinfo="text", colorscale="YlGnBu",
                    zmin=vmin, zmax=vmax, colorbar=dict(title="Precipitação (mm)"),
                    hoverongaps=False, showscale=True, zsmooth=False
                ))

                dias_por_mes = [calendar.monthrange(ano, m)[1] for m in range(1, 13)]
                for i in range(df_hm.shape[0]):
                    for j in range(df_hm.shape[1]):
                        if j >= dias_por_mes[i] or np.isnan(df_hm.iloc[i, j]):
                            fig.add_shape(
                                type="rect",
                                x0=float(df_hm.columns[j]) - 0.5, x1=float(df_hm.columns[j]) + 0.5,
                                y0=i - 0.5, y1=i + 0.5,
                                fillcolor="lightgray", line=dict(width=0), layer="above"
                            )
                fig.update_xaxes(tickmode="array", tickvals=dias, ticktext=[str(d) for d in dias], dtick=1)
                nome_legivel_sel = label_por_estacao.get(estacao, estacao)
                fig.update_layout(
                    template="plotly_white",
                    title=f"Precipitação diária — {nome_legivel_sel} — {ano}",
                    xaxis_title="Dia", yaxis_title="",
                    autosize=True, height=650, margin=dict(l=80, r=30, t=90, b=60),
                    font=dict(size=13)
                )
                grafico_html = fig.to_html(full_html=False, include_plotlyjs="cdn",
                                           config={"displaylogo": False, "responsive": True})

    return render(request, "siteapp/rede_de_estacoes_hobo.html", {
        "mapa_html": mapa_html,
        "grafico_html": grafico_html,
        "variaveis": variaveis,
        "variavel": variavel,
        "opcoes_estacoes": opcoes_estacoes,
        "estacao": estacao,
        "ano": ano,
        "escala": escala,
    })

# =============================================================================
# CONDIÇÕES ATUAIS — mapas Folium (Temperatura, PM2.5, Estações Virtuais)
# =============================================================================

VIEW_CENTER = (-3.11, -60.02)
VIEW_ZOOM   = 11
MAP_H_PX    = 720
LOGO_URL    = "/static/img/selva.png"

# BBox PurpleAir (Manaus)
MANAUS_BOUNDS = {"nwlng": -60.30, "nwlat": -2.90, "selng": -59.70, "selat": -3.35}

# Municípios RMM
MUNICIPIOS = [
    {"nome": "Manaus",                "lat": -3.117034, "lon": -60.025780},
    {"nome": "Manacapuru",            "lat": -3.299677, "lon": -60.621353},
    {"nome": "Iranduba",              "lat": -3.279088, "lon": -60.189230},
    {"nome": "Presidente Figueiredo", "lat": -2.048636, "lon": -60.023666},
    {"nome": "Rio Preto da Eva",      "lat": -2.698890, "lon": -59.700000},
    {"nome": "Itacoatiara",           "lat": -3.138610, "lon": -58.444960},
    {"nome": "Novo Airão",            "lat": -2.620830, "lon": -60.943890},
    {"nome": "Careiro da Várzea",     "lat": -3.199000, "lon": -59.822000},
    {"nome": "Autazes",               "lat": -3.579720, "lon": -59.130830},
    {"nome": "Careiro",               "lat": -3.768700, "lon": -60.368200},
    {"nome": "Itapiranga",            "lat": -2.740830, "lon": -58.029440},
    {"nome": "Manaquiri",             "lat": -3.441670, "lon": -60.461940},
    {"nome": "Silves",                "lat": -2.840830, "lon": -58.209440},
]

# colormaps / badges
TEMP_STOPS_18UP = [(18,'#73e5a3'), (20,'#90eb9d'), (30,'#f9d057'), (40,'#d7191c')]
TEMP_CMAP = LinearColormap(
    colors=[c for _, c in TEMP_STOPS_18UP],
    index=[v for v,_ in TEMP_STOPS_18UP], vmin=18, vmax=40
)
TEMP_CMAP.caption = "Temperatura do Ar (°C) – Simple correction (PurpleAir −8 °F)"

PM_BINS = [
    ("0–24.9",   "#39e639", "Boa"),
    ("25–49.9",  "#ffff00", "Moderada"),
    ("50–74.9",  "#f4a460", "Ruim"),
    ("75–124.9", "#ff3333", "Muito Ruim"),
    ("≥ 125",    "#a633cc", "Péssima"),
]

class LogoTopRight(MacroElement):
    _template = JinjaTemplate("""
        {% macro script(this, kwargs) %}
        var logoCtl = L.control({position: 'topright'});
        logoCtl.onAdd = function(map){
          var div = L.DomUtil.create('div', 'selva-logo');
          div.style.pointerEvents = 'none';
          div.style.margin = '{{this.margin}}px';
          var img = L.DomUtil.create('img', '', div);
          img.src = '{{this.image}}';
          img.style.width = '{{this.width}}px';
          img.style.opacity = '{{this.opacity}}';
          return div;
        };
        logoCtl.addTo({{ this._parent.get_name() }});
        {% endmacro %}
    """)
    def __init__(self, image, width=160, margin=10, opacity=1.0):
        super().__init__()
        self._name = "LogoTopRight"
        self.image = image; self.width = width; self.margin = margin; self.opacity = opacity

def _ts_manaus(epoch):
    if epoch is None: return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=ZoneInfo("UTC")).astimezone(TZ_AM)
    except Exception:
        return None

def _f_to_c(f): return (float(f) - 32.0) * 5/9
def _corr_selva_c(f):      return _f_to_c(f) - 2.0
def _corr_pa_simple_c(f):  return _f_to_c(float(f) - 8.0)

def _pm_color(pm):
    if pm is None: return "#9ca3af"
    if pm < 25:    return "#39e639"
    if pm < 50:    return "#ffff00"
    if pm < 75:    return "#f4a460"
    if pm < 125:   return "#ff3333"
    return "#a633cc"

def _rh_color(rh):
    if rh is None: return "#9ca3af"
    v = float(max(0, min(100, rh)))
    if v < 40:   return "#cfe8ff"
    if v < 60:   return "#7fb3ff"
    if v < 80:   return "#3d7dff"
    return "#0d47a1"

def _rain_color(mm):
    if mm is None or mm == 0: return "#9ca3af"
    if mm < 2:   return "#b3e5fc"
    if mm < 8:   return "#4fc3f7"
    if mm < 20:  return "#1e88e5"
    return "#6a1b9a"

def _badge_html(texto, bg_hex, size=34, bold=True, fg="#111"):
    fw = "700" if bold else "600"
    fs = 14 if size<=34 else 16
    return f"""
    <div style="width:{size}px;height:{size}px;border-radius:50%;
      background:{bg_hex};color:{fg};display:flex;align-items:center;justify-content:center;
      font-weight:{fw};font-size:{fs}px;line-height:1;box-shadow:0 0 0 1px #0003,0 2px 6px #0004;">
      {texto}
    </div>"""

def _chip(label):
    return f'<span style="display:inline-block;background:#6b7280;color:#fff;padding:2px 6px;border-radius:6px;font-size:11px;font-weight:700;">{label}</span>'

def _popup_html(name, lat, lon, pm, f_temp, f_a, f_b, dt_local):
    name = name or "Sensor"
    lat_s = f"{lat:.6f}" if lat is not None else "—"
    lon_s = f"{lon:.6f}" if lon is not None else "—"
    hora  = dt_local.strftime("%d/%m/%Y, %H:%M:%S") if dt_local else "—"
    def fmt(x, nd=1, suf="°C"): return f"{x:.{nd}f}{suf}" if x is not None else "—"
    c_raw   = _f_to_c(f_temp)            if f_temp is not None else None
    c_selva = _corr_selva_c(f_temp)      if f_temp is not None else None
    c_pa    = _corr_pa_simple_c(f_temp)  if f_temp is not None else None
    f_s   = f"{float(f_temp):.1f}°F" if f_temp is not None else "—"
    f_a_s = f"{float(f_a):.1f}°F"    if f_a is not None else "—"
    f_b_s = f"{float(f_b):.1f}°F"    if f_b is not None else "—"
    pm_txt = (f"{pm:.1f} µg/m³" if pm is not None else "—")
    return f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial;max-width:290px;">
      <div style="margin-bottom:6px;">{_chip('ESTAÇÃO')} <b>{name}</b></div>
      <div style="margin-bottom:6px;">{_chip('LAT')} {lat_s} &nbsp; {_chip('LON')} {lon_s}</div>
      <div style="margin:8px 0 6px;font-weight:700;">Temperatura (todas as versões)</div>
      <ul style="padding-left:18px;margin:0 0 6px 0;line-height:1.35;">
        <li><b>Simple correction (PurpleAir −8 °F):</b> {fmt(c_pa)}</li>
        <li><b>Corrigida SELVA (−2 °C):</b> {fmt(c_selva)}</li>
        <li><b>Sem correção:</b> {fmt(c_raw)}</li>
      </ul>
      <div style="margin:6px 0 6px 0;">{_chip('ORIGINAIS (°F)')} T={f_s} · A={f_a_s} · B={f_b_s}</div>
      <div style="margin-bottom:6px;">{_chip('QUALIDADE DO AR')} <b>{pm_txt}</b> PM2.5 (µg/m³)</div>
      <div style="margin-bottom:6px;">{_chip('ÚLTIMA LEITURA')} {hora} (Horário de Manaus-AM)</div>
      <div style="font-size:12px;color:#6b7280;font-style:italic;margin:4px 0 10px;">*não para fins regulatórios</div>
      <a href="/disclaimer" target="_blank" style="display:inline-block;background:#dc3545;color:#fff;text-decoration:none;padding:6px 12px;border-radius:6px;font-weight:700;">Disclaimer</a>
    </div>
    """

def _popup_virtual(lat, lon, t2, rh, rr, iso):
    lat_s = f"{lat:.6f}" if lat is not None else "—"
    lon_s = f"{lon:.6f}" if lon is not None else "—"
    hora  = datetime.fromisoformat(iso).strftime("%d/%m/%Y, %H:%M:%S") if iso else "—"
    def fmt(x, nd=1, suf=""): return f"{x:.{nd}f}{suf}" if x is not None else "—"
    return f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial;max-width:260px;">
      <div style="margin-bottom:6px;"><b>Estação Virtual (Open-Meteo)</b></div>
      <div style="margin-bottom:6px;">{_chip('LAT')} {lat_s} &nbsp; {_chip('LON')} {lon_s}</div>
      <ul style="padding-left:18px;margin:0 0 6px 0;line-height:1.35;">
        <li><b>Temperatura:</b> {fmt(t2,1,' °C')}</li>
        <li><b>Umidade Rel.:</b> {fmt(rh,0,' %')}</li>
        <li><b>Precipitação:</b> {fmt(rr,1,' mm/h')}</li>
      </ul>
      <div style="margin-bottom:6px;">{_chip('HORÁRIO LOCAL')} {hora}</div>
    </div>
    """

# cache helpers
def _cache_path(name): return os.path.join(MEDIA_CACHE_DIR, name)
def _read_cache(name):
    p = _cache_path(name)
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}
def _write_cache(name, data):
    p = _cache_path(name); tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)

# PurpleAir (cache 10 min)
PA_TTL = 600
def _get_purpleair():
    cache_js = _read_cache("purpleair.json")
    now = datetime.now(TZ_AM)
    ts  = cache_js.get("_ts")
    if ts:
        try:
            if (now - datetime.fromisoformat(ts)).total_seconds() <= PA_TTL:
                return cache_js.get("data", [])
        except Exception:
            pass
    data = []
    try:
        r = requests.get(
            "https://api.purpleair.com/v1/sensors",
            params={
                "fields": "latitude,longitude,name,pm2.5_10minute,pm2.5,pm2.5_atm,pm2.5_cf_1,temperature,temperature_a,temperature_b,last_seen",
                "location_type": 0, "max_age": 180, "limit": 250,
                "nwlng": MANAUS_BOUNDS["nwlng"], "nwlat": MANAUS_BOUNDS["nwlat"],
                "selng": MANAUS_BOUNDS["selng"], "selat": MANAUS_BOUNDS["selat"],
            },
            headers={"X-API-Key": PURPLEAIR_API_KEY}, timeout=12
        )
        if r.ok:
            js = r.json(); fields = js.get("fields", [])
            for row in js.get("data", []):
                s = dict(zip(fields, row))
                lat, lon = s.get("latitude"), s.get("longitude")
                if lat is None or lon is None:
                    continue
                pm = next((s.get(k) for k in ("pm2.5_10minute","pm2.5","pm2.5_atm","pm2.5_cf_1") if s.get(k) is not None), None)
                data.append({
                    "name": s.get("name"), "lat": lat, "lon": lon,
                    "pm": float(pm) if pm is not None else None,
                    "f_temp": float(s["temperature"])   if s.get("temperature")   is not None else None,
                    "f_a":    float(s["temperature_a"]) if s.get("temperature_a") is not None else None,
                    "f_b":    float(s["temperature_b"]) if s.get("temperature_b") is not None else None,
                    "dt": int(s.get("last_seen") or 0)
                })
            data.sort(key=lambda x: x["dt"] or 0, reverse=True)
            data = data[:120]
    except Exception:
        pass
    _write_cache("purpleair.json", {"_ts": now.isoformat(), "data": data})
    return data

# Open-Meteo em lote (cache 10 min)
OM_TTL = 600
PRIMARY_MODEL = "ecmwf_ifs"
def _get_openmeteo_batch_rmm():
    cache_js = _read_cache("openmeteo_rmm.json")
    now = datetime.now(TZ_AM)
    ts  = cache_js.get("_ts")
    if ts:
        try:
            if (now - datetime.fromisoformat(ts)).total_seconds() <= OM_TTL:
                return cache_js.get("data", [])
        except Exception:
            pass
    data = []
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry
        _cache = requests_cache.CachedSession(".cache_openmeteo", expire_after=3600)
        _session = retry(_cache, retries=2, backoff_factor=0.2)
        client = openmeteo_requests.Client(session=_session)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": [it["lat"] for it in MUNICIPIOS],
            "longitude": [it["lon"] for it in MUNICIPIOS],
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation"],
            "timezone": TZ,
            "models": PRIMARY_MODEL
        }
        responses = client.weather_api(url, params=params)
        for resp in responses:
            utc_offset = int(resp.UtcOffsetSeconds() or 0)
            cur = resp.Current()
            t2 = rh = rr = None; iso = None
            if cur and cur.VariablesLength() >= 3:
                t2 = float(cur.Variables(0).Value())
                rh = float(cur.Variables(1).Value())
                rr = float(cur.Variables(2).Value())
                t_loc = int(cur.Time()) + utc_offset
                iso = datetime.fromtimestamp(t_loc, TZ_AM).isoformat()
            data.append({"t2": t2, "rh": rh, "rain": rr, "iso": iso})
    except Exception:
        # fallback individual
        data = []
        for it in MUNICIPIOS:
            try:
                r = requests.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": it["lat"], "longitude": it["lon"],
                        "current": ["temperature_2m", "relative_humidity_2m", "precipitation"],
                        "timezone": TZ, "models": PRIMARY_MODEL
                    }, timeout=8
                )
                if not r.ok:
                    data.append({"t2": None, "rh": None, "rain": None, "iso": None}); continue
                cur = (r.json() or {}).get("current", {})
                data.append({
                    "t2": cur.get("temperature_2m"),
                    "rh": cur.get("relative_humidity_2m"),
                    "rain": cur.get("precipitation"),
                    "iso": cur.get("time")
                })
            except Exception:
                data.append({"t2": None, "rh": None, "rain": None, "iso": None})
    _write_cache("openmeteo_rmm.json", {"_ts": now.isoformat(), "data": data})
    return data

def _save_map(m: Map, filename: str) -> str:
    os.makedirs(MEDIA_MAPS_DIR, exist_ok=True)
    path = os.path.join(MEDIA_MAPS_DIR, filename)
    m.save(path)
    return f"/embed/maps/{filename}"

def _add_contorno_manaus(m: Map):
    p = finders.find("geo/contorno_manaus.geojson")
    if not p:
        p = os.path.join(settings.BASE_DIR, "static", "geo", "contorno_manaus.geojson")
    try:
        with open(p, "r", encoding="utf-8") as f:
            gj = json.load(f)
        folium.GeoJson(
            gj, name="Contorno de Manaus",
            style_function=lambda _:
                {"fillColor": "#0000", "color": "#145DA0", "weight": 3, "fillOpacity": 0.0},
            tooltip="Município de Manaus", show=True, control=False
        ).add_to(m)
    except Exception:
        pass

def _add_legend_pm25(m: Map):
    rows = "".join(
        f"<div style='display:flex;align-items:center;gap:8px;margin:2px 0'>"
        f"<span style='display:inline-block;width:16px;height:12px;background:{color};border-radius:3px;border:1px solid #0003'></span>"
        f"<span style='font-size:13px'>{label} µg/m³ — <b>{txt}</b></span>"
        f"</div>" for (label, color, txt) in PM_BINS
    )
    html = f"""
    <div style="position:fixed;z-index:9999;bottom:14px;left:14px;background:rgba(255,255,255,.95);
                padding:10px 12px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.25);
                font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:380px;">
      <div style="font-weight:700;font-size:14px;margin-bottom:6px;">Concentração de MP2.5 (µg/m³)</div>
      {rows}
      <div style="margin-top:6px;font-size:12px;color:#444">Referência: CONAMA/Brasil · Fonte: PurpleAir*</div>
      <div style="margin-top:2px;font-size:12px;color:#6b7280;font-style:italic;">*não para fins regulatórios</div>
    </div>"""
    m.get_root().html.add_child(Element(html))

def _add_legend_temp(m: Map, ticks=(18, 22, 26, 30, 34, 38, 40)):
    vmin, vmax = 18, 40
    parts = []
    for v, c in TEMP_STOPS_18UP:
        p = (v - vmin) / (vmax - vmin) * 100.0
        parts.append(f"{c} {p:.1f}%")
    grad = ", ".join(parts)
    ticks_html = "".join(f"<span>{t}</span>" for t in ticks)
    html = f"""
    <div style="position:fixed;z-index:9999;bottom:14px;left:14px;
                font-family:system-ui,Segoe UI,Arial;">
      <div style="background:rgba(255,255,255,.95);padding:10px 12px;
                  border-radius:14px;box-shadow:0 6px 18px rgba(0,0,0,.25);">
        <div style="width:260px;height:14px;border-radius:999px;
                    background:linear-gradient(90deg,{grad});
                    box-shadow:inset 0 1px 2px rgba(0,0,0,.25);"></div>
        <div style="display:flex;justify-content:space-between;
                    font-size:12px;margin-top:6px;">
          {ticks_html}
        </div>
      </div>
    </div>
    """
    m.get_root().html.add_child(Element(html))

def _map_temperatura_real() -> str:
    sensors = _get_purpleair()
    m = Map(location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM,
            tiles=None, control_scale=True, prefer_canvas=True, zoom_control=True)
    TileLayer('OpenStreetMap', control=False).add_to(m); Fullscreen(position="topleft", force_separate_button=True).add_to(m)
    m.add_child(LogoTopRight(LOGO_URL, width=160, margin=10, opacity=1.0))
    _add_contorno_manaus(m)
    for s in sensors:
        if s.get("f_temp") is None:
            continue
        t_corr = _corr_pa_simple_c(s["f_temp"])
        bg = '#9ca3af' if (t_corr is None or t_corr < 18) else TEMP_CMAP(t_corr)
        icon_html = _badge_html(f"{t_corr:.1f}°C", bg, size=34, bold=True, fg="#111")
        popup_html = _popup_html(s["name"], s["lat"], s["lon"], s["pm"],
                                 s["f_temp"], s["f_a"], s["f_b"], _ts_manaus(s["dt"]))
        Marker([s["lat"], s["lon"]],
               tooltip=s["name"] or "Sensor",
               popup=folium.Popup(popup_html, max_width=320),
               icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_html)
        ).add_to(m)
    _add_legend_temp(m)
    return _save_map(m, "mapa_temp_real.html")

def _map_qualidade_ar() -> str:
    sensors = _get_purpleair()
    m = Map(location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM,
            tiles=None, control_scale=True, prefer_canvas=True, zoom_control=True)
    TileLayer('OpenStreetMap', control=False).add_to(m); Fullscreen(position="topleft", force_separate_button=True).add_to(m)
    m.add_child(LogoTopRight(LOGO_URL, width=160, margin=10, opacity=1.0))
    _add_contorno_manaus(m)
    for s in sensors:
        pm = s.get("pm")
        if pm is None: continue
        bg = _pm_color(pm)
        icon_html = _badge_html(f"{pm:.1f}", bg, size=34, bold=True, fg="#111")
        popup_html = _popup_html(s["name"], s["lat"], s["lon"], pm,
                                 s["f_temp"], s["f_a"], s["f_b"], _ts_manaus(s["dt"]))
        Marker([s["lat"], s["lon"]],
               tooltip=s["name"] or "Sensor",
               popup=folium.Popup(popup_html, max_width=320),
               icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_html)
        ).add_to(m)
    _add_legend_pm25(m)
    return _save_map(m, "mapa_pm25.html")

def _map_estacoes_virtuais() -> str:
    lote = _get_openmeteo_batch_rmm()
    m = Map(location=[-3.2, -60.0], zoom_start=8,
            tiles=None, control_scale=True, prefer_canvas=True)
    TileLayer('OpenStreetMap', control=False).add_to(m); Fullscreen(position="topleft", force_separate_button=True).add_to(m)
    m.add_child(LogoTopRight(LOGO_URL, width=160, margin=10, opacity=1.0))
    # contorno idêntico
    _add_contorno_manaus(m)

    layer_t  = folium.FeatureGroup(name="Temperatura (virtual)", show=True)
    layer_rh = folium.FeatureGroup(name="Umidade Relativa (virtual)", show=False)
    layer_rr = folium.FeatureGroup(name="Chuva (virtual)", show=False)

    for idx, it in enumerate(MUNICIPIOS):
        lat, lon, nome = it["lat"], it["lon"], it["nome"]
        rec = lote[idx] if idx < len(lote) else {}
        t2, rh, rr, iso = rec.get("t2"), rec.get("rh"), rec.get("rain"), rec.get("iso")

        if t2 is not None:
            bg_t = TEMP_CMAP(float(max(18, min(40, t2)))) if t2 >= 18 else "#9ca3af"
            icon_t = _badge_html(f"{t2:.1f}°C", bg_t, size=34, bold=True, fg="#111")
            folium.Marker([lat, lon],
                tooltip=f"{nome} – Temperatura",
                popup=folium.Popup(_popup_virtual(lat, lon, t2, rh, rr, iso), max_width=320),
                icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_t)
            ).add_to(layer_t)

        if rh is not None:
            bg_h = _rh_color(rh)
            icon_h = _badge_html(f"{rh:.0f}%", bg_h, size=34, bold=True, fg="#111")
            folium.Marker([lat, lon],
                tooltip=f"{nome} – Umidade Relativa",
                popup=folium.Popup(_popup_virtual(lat, lon, t2, rh, rr, iso), max_width=320),
                icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_h)
            ).add_to(layer_rh)

        if rr is not None:
            bg_r = _rain_color(rr)
            icon_r = _badge_html(f"{rr:.1f}", bg_r, size=34, bold=True, fg="#111")
            folium.Marker([lat, lon],
                tooltip=f"{nome} – Chuva (mm/h)",
                popup=folium.Popup(_popup_virtual(lat, lon, t2, rh, rr, iso), max_width=320),
                icon=DivIcon(icon_size=(34,34), icon_anchor=(17,17), html=icon_r)
            ).add_to(layer_rr)

    layer_t.add_to(m); layer_rh.add_to(m); layer_rr.add_to(m)
    folium.LayerControl(collapsed=False, position="topleft").add_to(m)

    # enquadramento RMM
    try:
        lats = [it["lat"] for it in MUNICIPIOS]; lons = [it["lon"] for it in MUNICIPIOS]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(10, 10))
    except Exception:
        pass

    _add_legend_temp(m)
    return _save_map(m, "mapa_virtuais_rmm.html")

def condicoes_atmosfera(request):
    # Gera/atualiza mapas e entrega iframes
    temp_iframe = _map_temperatura_real()
    ar_iframe   = _map_qualidade_ar()
    virt_iframe = _map_estacoes_virtuais()
    ctx = {
        "mapa_temp_iframe": temp_iframe,
        "mapa_ar_iframe":   ar_iframe,
        "mapa_virt_iframe": virt_iframe,
        "map_height": MAP_H_PX,
        "proxima": (datetime.now(TZ_AM) + timedelta(minutes=10)).strftime("%H:%M"),
        "temp_cmap_json": json.dumps(TEMP_STOPS_18UP),
    }
    return render(request, "siteapp/condicoes.html", ctx)

@xframe_options_exempt
def embed_map(request, fname: str):
    """Serve /media/maps/<fname> como text/html, liberado para <iframe>."""
    base = os.path.join(settings.MEDIA_ROOT, "maps")
    try:
        path = safe_join(base, fname)
    except Exception:
        raise Http404()
    if not os.path.exists(path):
        raise Http404()
    return FileResponse(open(path, "rb"), content_type="text/html")






def agrometeorologia(request):
    return render(request, "siteapp/agrometeorologia.html", {"current": "agrometeorologia"})

def energia_solar(request):
    return render(request, "siteapp/produtos/energia_solar.html")

def construcao_civil(request):
    return render(request, "siteapp/produtos/construcao_civil.html")

def educacao_ambiental(request):
    return render(request, "siteapp/produtos/educacao_ambiental.html")







# =============================================================================
# PÁGINA Satélite & Radar (comparador) — usa iframes dos mapas gerados
# =============================================================================
def satelite_radar(request):
    # Garante que existem arquivos atualizados para os painéis "Temperatura" e "Qualidade do Ar"
    temp_iframe = _map_temperatura_real()
    ar_iframe   = _map_qualidade_ar()

    context = {
        "agora": datetime.now(TZ_AM).strftime('%d/%m/%Y, %H:%M:%S'),
        "mapa_temp_iframe": temp_iframe,     # ex.: /embed/maps/mapa_temp_real.html
        "mapa_ar_iframe":   ar_iframe,       # ex.: /embed/maps/mapa_pm25.html
        "youtube_channel_id": "",            # se tiver canal ao vivo, coloque o ID aqui
        "map_height": 620,
    }
    return render(request, "siteapp/satelite_radar.html", context)

# (Compatível com seus caminhos antigos — redireciona para o mapa gerado)
@xframe_options_exempt
def mapa_temp_real(request):
    return redirect(_map_temperatura_real())

@xframe_options_exempt
def mapa_pm25(request):
    return redirect(_map_qualidade_ar())

# =============================================================================
# CONTATO — envio por Gmail (senha de app)
# =============================================================================
def _fmt_err(e):
    eno = getattr(e, "errno", None)
    if isinstance(e, (socket.error, OSError)):
        return f"{e.__class__.__name__} (errno={eno}) {e}"
    return f"{e.__class__.__name__}: {e}"

def _enviar_gmail(subject: str, body: str, reply_to_email: str | None):
    if not GMAIL_APP_PASSWORD or len(GMAIL_APP_PASSWORD) != 16:
        return False, "Senha de app inválida (precisa ter 16 caracteres)."
    # 1) SSL 465
    try:
        conn_ssl = get_connection(
            host="smtp.gmail.com", port=465,
            username=SENDER_EMAIL, password=GMAIL_APP_PASSWORD,
            use_ssl=True, timeout=20,
        )
        EmailMessage(
            subject=subject, body=body,
            from_email=FROM_EMAIL_FMT, to=TO_LIST,
            reply_to=[reply_to_email] if reply_to_email else None,
            connection=conn_ssl,
        ).send()
        return True, "via Gmail SSL 465"
    except Exception as e_ssl:
        err_ssl = e_ssl
    # 2) TLS 587
    try:
        conn_tls = get_connection(
            host="smtp.gmail.com", port=587,
            username=SENDER_EMAIL, password=GMAIL_APP_PASSWORD,
            use_tls=True, timeout=20,
        )
        EmailMessage(
            subject=subject, body=body,
            from_email=FROM_EMAIL_FMT, to=TO_LIST,
            reply_to=[reply_to_email] if reply_to_email else None,
            connection=conn_tls,
        ).send()
        return True, "via Gmail TLS 587"
    except Exception as e_tls:
        return False, f"SSL falhou: {_fmt_err(err_ssl)} | TLS falhou: {_fmt_err(e_tls)}"

def contato(request):
    context = {}
    if request.method == "POST":
        campos = ["nome","email","instituicao","curso_nivel","numero_alunos","objetivo","assunto","mensagem"]
        data = {k: (request.POST.get(k,"") or "").strip() for k in campos}
        honeypot = (request.POST.get("website","") or "").strip()

        if honeypot:
            messages.success(request, "Mensagem enviada com sucesso!")
            return redirect("contato")

        errors = {}
        if not data["nome"]:
            errors["nome"] = "Informe seu nome completo."
        try:
            validate_email(data["email"])
        except ValidationError:
            errors["email"] = "E-mail inválido."
        if not data["instituicao"]:
            errors["instituicao"] = "Informe a instituição."
        if not data["curso_nivel"]:
            errors["curso_nivel"] = "Informe o curso/nível."
        if not data["numero_alunos"]:
            errors["numero_alunos"] = "Informe o número de alunos."
        else:
            try:
                if int(data["numero_alunos"]) < 1:
                    errors["numero_alunos"] = "Deve ser pelo menos 1."
            except ValueError:
                errors["numero_alunos"] = "Use apenas números inteiros."
        if not data["objetivo"]:
            errors["objetivo"] = "Descreva o objetivo da visita."

        if errors:
            context["errors"] = errors
            context["post"] = data
            messages.error(request, "Por favor, verifique os campos destacados.")
            return render(request, "siteapp/contato.html", context)

        assunto = data["assunto"] or "Agendamento de visita – LabInstru"
        corpo = (
            "📨 Nova solicitação de contato/agendamento\n\n"
            f"Nome: {data['nome']}\n"
            f"E-mail: {data['email']}\n"
            f"Instituição: {data['instituicao']}\n"
            f"Curso/Nível: {data['curso_nivel']}\n"
            f"Nº de alunos: {data['numero_alunos']}\n"
            f"Objetivo da visita: {data['objetivo']}\n\n"
            f"Mensagem complementar:\n{(data['mensagem'] or '(sem mensagem)')}\n"
        )
        try:
            ok, detalhe = _enviar_gmail(assunto, corpo, data["email"])
            if ok:
                messages.success(request, f"Mensagem enviada com sucesso ({detalhe}).")
                return redirect("contato")
            else:
                context["post"] = data
                messages.error(request,
                    "Erro ao enviar: " + detalhe +
                    "\nDicas: 1) Confirme que o 2FA está ativo; "
                    "2) Em contas Workspace, o admin pode bloquear senhas de app; "
                    "3) Alguns hosts bloqueiam 465/587."
                )
                return render(request, "siteapp/contato.html", context)
        except BadHeaderError:
            context["post"] = data
            messages.error(request, "Cabeçalho inválido no e-mail.")
            return render(request, "siteapp/contato.html", context)
    return render(request, "siteapp/contato.html", context)







from django.shortcuts import render

def app_labinstru(request):
    return render(request, "siteapp/app_labinstru.html")




# >>> VIEW PRINCIPAL DA PÁGINA "TEMPO AGORA"
def condicoes_atmosfera(request):
    temp_iframe = _map_temperatura_real()  # ex: "/embed/maps/mapa_temp_real.html"
    ar_iframe   = _map_qualidade_ar()      # ex: "/embed/maps/mapa_pm25.html"
    virt_iframe = _map_estacoes_virtuais() # ex: "/embed/maps/mapa_virtuais_rmm.html"

    ctx = {
        "mapa_temp_iframe": temp_iframe,
        "mapa_ar_iframe":   ar_iframe,
        "mapa_virt_iframe": virt_iframe,
        "map_height": 720,
        "proxima": (datetime.now(ZoneInfo("America/Manaus")) + timedelta(minutes=10)).strftime("%H:%M"),
        "temp_cmap_json": json.dumps(TEMP_STOPS_18UP),
    }
    return render(request, "siteapp/condicoes.html", ctx)


# >>> ESTA VIEW SERVE O HTML GERADO PELO FOLIUM (SEM REDIRECT)
@xframe_options_exempt
def embed_map(request, filename):
    """
    Responde /embed/maps/<filename> devolvendo o arquivo HTML
    salvo em media/maps/<filename> (mapa gerado pelo Folium).
    """
    file_path = os.path.join(settings.MEDIA_ROOT, "maps", filename)

    if not os.path.exists(file_path):
        raise Http404("Mapa não encontrado.")

    return FileResponse(open(file_path, "rb"), content_type="text/html")















# =============================================================================
# PAINEL INMET (tempo real / diário / semanal / mensal / climatologia / alertas)
# =============================================================================

NORTH_STATES = ["Amazonas", "Roraima", "Rondônia", "Acre", "Pará", "Mato Grosso"]
IBGE_PREFIXES_NORTH = {"13", "14", "11", "12", "15", "51"}

def _dbg(msg: str) -> None:
    print(f"[INMET] {msg}")

def _as_manaus(ts) -> Optional[pd.Timestamp]:
    if ts is None:
        return None
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        return ts.tz_localize(TZ_AM, nonexistent="shift_forward", ambiguous="NaT")
    return ts.tz_convert(TZ_AM)

def _fmt_hora_manaus(ts: pd.Timestamp) -> str:
    ts = _as_manaus(ts)
    return ts.strftime("%H:%M (Manaus)") if ts is not None else "— (Manaus)"

def _fmt_data_manaus(ts) -> str:
    ts = _as_manaus(ts)
    return ts.strftime("%d/%m/%Y") if ts is not None else "—/—/—"

def _fmt_hhmm_manaus(ts) -> str:
    ts = _as_manaus(ts)
    return ts.strftime("%H:%M") if ts is not None else "—:—"

def get_station_data(station: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    url = f"https://apitempo.inmet.gov.br/token/estacao/{start_date}/{end_date}/{station}/{INMET_TOKEN}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, "Sem dados (API vazia)."
        df = pd.DataFrame(data)
        num_cols = ["TEM_INS","UMD_INS","PRE_INS","VEN_VEL","CHUVA","PTO_INS","RAD_GLO","RAD","RAD_GLOBAL","GL_RAD","RAD_S","RS","RADIACAO"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "DT_MEDICAO" not in df.columns or "HR_MEDICAO" not in df.columns:
            return None, "Campos de data/hora ausentes."
        hr = df["HR_MEDICAO"].astype(str).str.extract(r"(\d+)")[0].fillna("0000").str.zfill(4)
        dt_str = df["DT_MEDICAO"].astype(str) + " " + hr
        ts_utc = pd.to_datetime(dt_str, format="%Y-%m-%d %H%M", errors="coerce", utc=True)
        mask = ts_utc.notna()
        if not mask.any():
            return None, "Falha ao interpretar datas/horas."
        idx = pd.DatetimeIndex(ts_utc[mask]).tz_convert(TZ_AM)
        df = df.loc[mask].copy(); df.index = idx; df.sort_index(inplace=True)
        return df, None
    except Exception as e:
        return None, f"Erro API: {e}"

def _last_valid(df: pd.DataFrame, col: str):
    try:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            return None, None
        return float(s.iloc[-1]), s.index[-1]
    except Exception:
        return None, None

def _heat_index_celsius(t_c: Optional[float], rh: Optional[float]) -> Optional[float]:
    if t_c is None or rh is None or pd.isna(t_c) or pd.isna(rh):
        return None
    if t_c < 20 or rh < 40:
        return t_c
    t_f = t_c * 9 / 5 + 32.0
    r = float(rh)
    c1 = -42.379; c2 = 2.04901523; c3 = 10.14333127
    c4 = -0.22475541; c5 = -0.00683783; c6 = -0.05481717
    c7 = 0.00122874; c8 = 0.00085282; c9 = -0.00000199
    hi_f = (c1 + c2*t_f + c3*r + c4*t_f*r + c5*t_f*t_f + c6*r*r +
            c7*t_f*t_f*r + c8*t_f*r*r + c9*t_f*t_f*r*r)
    if r < 13 and (80 <= t_f <= 112):
        hi_f -= ((13 - r) / 4) * ((17 - abs(t_f - 95)) / 17) ** 0.5
    elif r > 85 and (80 <= t_f <= 87):
        hi_f += ((r - 85) / 10) * ((87 - t_f) / 5)
    return float((hi_f - 32) * 5 / 9)

def _pick_rad_column(df: pd.DataFrame) -> Optional[str]:
    for c in ["RAD_GLO", "RAD", "RAD_GLOBAL", "GL_RAD", "RAD_S", "RS", "RADIACAO"]:
        if c in df.columns:
            return c
    return None

def _daily_insolation_kj_m2(df: pd.DataFrame, col: str) -> Optional[float]:
    if not col or df.empty:
        return None
    last_day = df.index.max().date()
    d = df[df.index.date == last_day][col].dropna()
    if d.empty:
        return None
    vmax = float(d.max())
    if vmax < 50:        # MJ/m²
        return float(d.sum() * 1000)
    if vmax <= 5000:     # kJ/m²
        return float(d.sum())
    return float((d * 3.6).sum())  # W/m²·h -> kJ/m²

MESES_ORD = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
PERIODOS = ["1931 - 1960", "1961 - 1990", "1991 - 2020"]

def _static_data_path(rel_path: str) -> Path:
    rel_path = rel_path.replace("\\", "/")
    abs_path = None
    if finders:
        abs_path = finders.find(rel_path) or finders.find(f"dados/{Path(rel_path).name}")
    if abs_path:
        return Path(abs_path)
    base = Path(getattr(settings, "BASE_DIR", ".")) / "static"
    p = base / rel_path
    if not p.exists():
        p2 = base / "dados" / Path(rel_path).name
        return p2
    return p

def _fmt_mes_label(x) -> str:
    try:
        i = int(x)
        return MESES_ORD[i-1] if 1 <= i <= 12 else str(x)
    except Exception:
        s = str(x).strip().title()[:3]
        mapa = {"Jan":"Jan","Fev":"Fev","Mar":"Mar","Abr":"Abr","Mai":"Mai","Jun":"Jun",
                "Jul":"Jul","Ago":"Ago","Set":"Set","Out":"Out","Nov":"Nov","Dez":"Dez"}
        return mapa.get(s, s)

def _df_from_csv_any(csv_rel: str) -> pd.DataFrame:
    path = _static_data_path(f"dados/{csv_rel}")
    df = pd.read_csv(path)
    cols = [c.strip() for c in df.columns]
    df.columns = cols
    is_period = ("Category" in cols) and any(p in cols for p in PERIODOS)
    if is_period:
        use_periods = [p for p in PERIODOS if p in cols]
        df_long = df.melt(id_vars=["Category"], value_vars=use_periods,
                          var_name="periodo", value_name="valor")
        df_long["mes"] = df_long["Category"].map(_fmt_mes_label)
        df_long.drop(columns=["Category"], inplace=True)
        df_long["__ord"] = df_long["mes"].apply(lambda m: MESES_ORD.index(m) if m in MESES_ORD else 999)
        df_long = df_long.sort_values(["__ord","periodo"]).drop(columns="__ord")
        df_long["valor"] = pd.to_numeric(df_long["valor"], errors="coerce")
        return df_long[["mes","periodo","valor"]]
    col_mes = "mes" if "mes" in cols else cols[0]
    col_val = "valor" if "valor" in cols else (cols[1] if len(cols) > 1 else None)
    if col_val is None:
        raise ValueError(f"CSV {csv_rel} sem coluna de valores.")
    df_simple = df.rename(columns={col_mes: "mes", col_val: "valor"})[["mes","valor"]].copy()
    df_simple["mes"] = df_simple["mes"].map(_fmt_mes_label)
    df_simple["__ord"] = df_simple["mes"].apply(lambda m: MESES_ORD.index(m) if m in MESES_ORD else 999)
    df_simple = df_simple.sort_values("__ord").drop(columns="__ord")
    df_simple["valor"] = pd.to_numeric(df_simple["valor"], errors="coerce")
    return df_simple

def _plot_line_periodos(df_long: pd.DataFrame, ylab="°C") -> str:
    fig = px.line(df_long, x="mes", y="valor", color="periodo", markers=True,
                  category_orders={"mes": MESES_ORD, "periodo": PERIODOS},
                  color_discrete_sequence=["#2563eb", "#10b981", "#f59e0b"])
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=30,b=10),
                      xaxis_title="Mês", yaxis_title=ylab, template="plotly_white",
                      legend_title="Período")
    return fig.to_html(include_plotlyjs="cdn", full_html=False)

def _plot_line_simple(df_simple: pd.DataFrame, ylab="°C") -> str:
    fig = px.line(df_simple, x="mes", y="valor", markers=True,
                  category_orders={"mes": MESES_ORD})
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=30,b=10),
                      xaxis_title="Mês", yaxis_title=ylab, template="plotly_white")
    return fig.to_html(include_plotlyjs="cdn", full_html=False)

def _plot_bar_periodos(df_long: pd.DataFrame, ylab="mm") -> str:
    fig = px.bar(df_long, x="mes", y="valor", color="periodo", barmode="group",
                 category_orders={"mes": MESES_ORD, "periodo": PERIODOS},
                 color_discrete_sequence=["#2563eb", "#10b981", "#f59e0b"])
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=30,b=10),
                      xaxis_title="Mês", yaxis_title=ylab, template="plotly_white",
                      legend_title="Período")
    return fig.to_html(include_plotlyjs="cdn", full_html=False)

def _plot_bar_simple(df_simple: pd.DataFrame, ylab="mm") -> str:
    fig = px.bar(df_simple, x="mes", y="valor", category_orders={"mes": MESES_ORD})
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=30,b=10),
                      xaxis_title="Mês", yaxis_title=ylab, template="plotly_white")
    return fig.to_html(include_plotlyjs="cdn", full_html=False)

def _fmt_date_str(iso_str: str) -> str:
    if not iso_str:
        return "—"
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(iso_str, fmt).strftime("%d/%m/%Y")
        except Exception:
            pass
    return "—"

def _enrich_alert(av: dict, prefixes_ibge: set) -> dict:
    av = dict(av)
    av["data_inicio_formatado"] = _fmt_date_str(av.get("data_inicio"))
    av["data_fim_formatado"]    = _fmt_date_str(av.get("data_fim"))
    riscos = av.get("riscos"); instr  = av.get("instrucoes")
    av["riscos_txt"] = ". ".join([str(x) for x in riscos]) if isinstance(riscos, list) else (riscos or "—")
    av["instr_txt"]  = ". ".join([str(x) for x in instr])  if isinstance(instr,  list) else (instr  or "—")
    av["areas_afetadas"] = av.get("areas_afetadas") or av.get("areas") or "—"
    av["aviso_cor"] = av.get("aviso_cor") or "#ffd300"
    if av.get("municipios"):
        av["municipios_view"] = ", ".join(av["municipios"]) if isinstance(av["municipios"], list) else str(av["municipios"])
    else:
        geocodes_raw = av.get("geocodes", "") or ""
        cods = [c.strip() for c in geocodes_raw.split(",") if c.strip()]
        cods_sel = [c for c in cods if c[:2] in prefixes_ibge or any(c.startswith(p) for p in prefixes_ibge)]
        av["municipios_view"] = ", ".join(cods_sel) if cods_sel else "—"
    return av

def build_alert_fc(tempo_key: str = "hoje") -> Tuple[str, Optional[dict], Optional[str]]:
    try:
        url = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
        r = requests.get(url, timeout=20); r.raise_for_status()
        data = r.json()
    except Exception as e:
        return json.dumps({"type":"FeatureCollection","features":[]}), None, f"Falha na API de avisos ({e})"
    if not isinstance(data, dict) or tempo_key not in data:
        return json.dumps({"type":"FeatureCollection","features":[]}), None, "Resposta inesperada dos avisos do INMET."
    feats = []; first_props = None
    for av in data[tempo_key]:
        estados = av.get("estados") or []
        if not any(uf in estados for uf in NORTH_STATES):
            continue
        try:
            geom = json.loads(av.get("poligono", "{}"))
        except Exception:
            continue
        props = _enrich_alert(av, IBGE_PREFIXES_NORTH)
        if first_props is None:
            first_props = props
        feats.append({"type":"Feature", "geometry": geom, "properties": props})
    fc = {"type":"FeatureCollection", "features": feats}
    return json.dumps(fc, ensure_ascii=False), first_props, (None if feats else "Sem alertas ativos na Região Norte/MT.")

def inmet_painel(request, station: str = "A101"):
    tab = request.GET.get("tab", "tempo")
    cache_key = f"inmet_panel_{station}"
    if request.GET.get("flush") == "1":
        cache.delete(cache_key)
    ctx = cache.get(cache_key)
    if ctx is None:
        now = datetime.now(TZ_AM); today = now.date()
        week_start_api = (now - timedelta(days=8)).strftime("%Y-%m-%d")
        today_api = now.strftime("%Y-%m-%d")
        month_start = now.replace(day=1).date()
        month_last_day = calendar.monthrange(now.year, now.month)[1]
        month_end = datetime(now.year, now.month, month_last_day, tzinfo=TZ_AM).date()
        month_end_for_axis = min(today, month_end)
        df_week, err_w = get_station_data(station, week_start_api, today_api)
        df_month, err_m = get_station_data(station, month_start.strftime("%Y-%m-%d"), today_api)
        api_error = err_w if (df_week is None and err_w) else (err_m if (df_month is None and err_m) else None)
        station_lat, station_lon = HARDCODED_COORDS.get(station, (-3.118, -60.021))
        station_name = f"INMET {station}"

        # Tempo real
        update_time = "— (Manaus)"; update_date = "—/—/—"
        rt_temp_value = rt_feels_value = rt_humi_value = rt_pres_value = rt_wind_value = "—"
        rt_insol_value = "—"
        if isinstance(df_week, pd.DataFrame) and not df_week.empty:
            ts_candidates: List[pd.Timestamp] = []
            for col in ["TEM_INS","UMD_INS","PRE_INS","VEN_VEL","CHUVA"]:
                _, ts = _last_valid(df_week, col)
                if ts is not None: ts_candidates.append(ts)
            if ts_candidates:
                last_ts = max(ts_candidates); update_time = _fmt_hora_manaus(last_ts); update_date = _fmt_data_manaus(last_ts)
            t, _ = _last_valid(df_week, "TEM_INS")
            u, _ = _last_valid(df_week, "UMD_INS")
            p, _ = _last_valid(df_week, "PRE_INS")
            v_ms, _ = _last_valid(df_week, "VEN_VEL")
            rad_col = _pick_rad_column(df_week)
            insol_kj = _daily_insolation_kj_m2(df_week, rad_col) if rad_col else None
            hi = _heat_index_celsius(t, u)
            dew, _ = _last_valid(df_week, "PTO_INS")
            if t is not None: rt_temp_value = f"{t:.1f}"
            if hi is not None: rt_feels_value = f"{hi:.1f}"
            elif dew is not None: rt_feels_value = f"{dew:.1f}"
            elif t is not None: rt_feels_value = f"{t:.1f}"
            if u is not None: rt_humi_value = f"{u:.0f}"
            if p is not None: rt_pres_value = f"{p:.0f}"
            if v_ms is not None: rt_wind_value = f"{v_ms:.1f}"
            if insol_kj is not None: rt_insol_value = f"{insol_kj:.0f}"

        # Diário
        graph_daily = '<div class="alert alert-info m-0">Sem dados do dia.</div>'
        pill_diario = "Sem dados para o dia."
        try:
            if isinstance(df_week, pd.DataFrame) and not df_week.empty:
                day_with_data = None
                if "TEM_INS" in df_week.columns:
                    s = pd.to_numeric(df_week["TEM_INS"], errors="coerce").dropna()
                    if not s.empty: day_with_data = s.index[-1].date()
                if day_with_data is None and not df_week.dropna(how="all").empty:
                    day_with_data = df_week.dropna(how="all").index.max().date()
                if day_with_data is not None:
                    dft = df_week[df_week.index.date == day_with_data].copy()
                    chuva = float(dft["CHUVA"].sum(min_count=1) or 0) if "CHUVA" in dft else 0.0
                    tmin = tmax = None; tmin_h = tmax_h = "—:—"
                    if "TEM_INS" in dft:
                        tser = pd.to_numeric(dft["TEM_INS"], errors="coerce")
                        if tser.notna().any():
                            tmin = float(tser.min());  tmin_ts = tser.idxmin()
                            tmax = float(tser.max());  tmax_ts = tser.idxmax()
                            tmin_h = _fmt_hhmm_manaus(tmin_ts); tmax_h = _fmt_hhmm_manaus(tmax_ts)
                    pill_diario = (
                        f"Dia {day_with_data.strftime('%d/%m/%Y')} · "
                        f"Mín {('—' if tmin is None else f'{tmin:.1f}')} °C ({tmin_h}) · "
                        f"Máx {('—' if tmax is None else f'{tmax:.1f}')} °C ({tmax_h}) · "
                        f"Chuva {chuva:.1f} mm"
                    )
                    fig = go.Figure()
                    if "CHUVA" in dft:
                        fig.add_trace(go.Bar(x=dft.index, y=dft["CHUVA"].fillna(0),
                                             name="Precipitação (mm)", opacity=0.55, marker_line_width=0, yaxis="y3"))
                    if "UMD_INS" in dft:
                        fig.add_trace(go.Scatter(x=dft.index, y=dft["UMD_INS"],
                                                 name="Umidade (%)", mode="lines+markers",
                                                 line=dict(dash="dot", width=2, color="#f97316"),
                                                 marker=dict(size=6), yaxis="y2"))
                    if "TEM_INS" in dft:
                        fig.add_trace(go.Scatter(x=dft.index, y=dft["TEM_INS"],
                                                 name="Temperatura (°C)", mode="lines+markers",
                                                 line=dict(color="#16a34a", width=3),
                                                 marker=dict(size=6), yaxis="y1"))
                    fig.update_layout(
                        title=f"Condições do Dia — {day_with_data.strftime('%d/%m/%Y')} (Hora Manaus)",
                        xaxis=dict(title="Horas (America/Manaus)", tickformat="%H:%M", showgrid=True),
                        yaxis=dict(title="Temperatura (°C)", showgrid=True, position=0.06),
                        yaxis2=dict(title="Umidade (%)", overlaying="y", side="right", showgrid=False),
                        yaxis3=dict(title="Precipitação (mm)", overlaying="y", side="left", position=0.0, showgrid=False),
                        legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"),
                        margin=dict(t=60, b=50, l=60, r=60),
                        template="plotly_white", height=430
                    )
                    day0 = pd.Timestamp(day_with_data, tz=TZ_AM)
                    fig.update_xaxes(range=[day0, day0 + pd.Timedelta(hours=23, minutes=59, seconds=59)],
                                     dtick=3 * 3600_000, tickformat="%H:%M")
                    graph_daily = fig.to_html(full_html=False, include_plotlyjs="cdn")
        except Exception as e:
            _dbg(f"ERRO gráfico diário: {e}")

        # Semanal
        graph_week_combo = '<div class="alert alert-info m-0">Sem dados semanais.</div>'
        week_tmax = week_tmin = week_rain_total = "—"
        week_rain_days = week_dry_days = 0
        week_tmax_day = week_tmin_day = "—"
        week_temp_avg = "—"
        try:
            if isinstance(df_week, pd.DataFrame) and not df_week.empty:
                end7 = today; start7 = end7 - timedelta(days=6)
                w = df_week[(df_week.index.date >= start7) & (df_week.index.date <= end7)].copy()
                have_temp = "TEM_INS" in w.columns; have_rain = "CHUVA" in w.columns
                if have_temp or have_rain:
                    by_day = w.groupby(w.index.normalize()).agg(
                        **({"Tmax": ("TEM_INS", "max"),
                            "Tmin": ("TEM_INS", "min"),
                            "Tmean": ("TEM_INS", "mean")} if have_temp else {}),
                        **({"Chuva": ("CHUVA", "sum")} if have_rain else {}),
                    )
                    idx7 = pd.date_range(start=pd.Timestamp(start7, tz=TZ_AM), end=pd.Timestamp(end7, tz=TZ_AM), freq="D")
                    daily = by_day.reindex(idx7)
                    if "Chuva" in daily.columns: daily["Chuva"] = daily["Chuva"].fillna(0)
                    if "Tmax" in daily.columns and daily["Tmax"].notna().any():
                        tmax_val = float(daily["Tmax"].max()); week_tmax = f"{tmax_val:.1f}"
                        week_tmax_day = pd.Timestamp(daily["Tmax"].astype(float).idxmax()).strftime("%d/%m")
                    if "Tmin" in daily.columns and daily["Tmin"].notna().any():
                        tmin_val = float(daily["Tmin"].min()); week_tmin = f"{tmin_val:.1f}"
                        week_tmin_day = pd.Timestamp(daily["Tmin"].astype(float).idxmin()).strftime("%d/%m")
                    if have_temp and w["TEM_INS"].notna().any():
                        week_temp_avg = f"{float(w['TEM_INS'].mean()):.1f}"
                    if "Chuva" in daily.columns:
                        week_rain_total = f"{float(daily['Chuva'].sum()):.1f}"
                        week_rain_days = int((daily["Chuva"] > 0).sum())
                        week_dry_days  = int((daily["Chuva"] <= 0).sum())

                    figw = go.Figure()
                    if "Chuva" in daily.columns:
                        figw.add_trace(go.Bar(x=daily.index, y=daily["Chuva"], name="Chuva (mm)",
                                              opacity=0.55, marker_line_width=0, yaxis="y2"))
                    if "Tmax" in daily.columns:
                        figw.add_trace(go.Scatter(x=daily.index, y=daily["Tmax"], name="Temp máx (°C)",
                                                  mode="lines+markers", line=dict(color="#ef4444", width=3)))
                    if "Tmin" in daily.columns:
                        figw.add_trace(go.Scatter(x=daily.index, y=daily["Tmin"], name="Temp mín (°C)",
                                                  mode="lines+markers", line=dict(color="#10b981", width=3)))
                    figw.update_layout(
                        title="Semana — Temperaturas e Chuva",
                        xaxis=dict(title="Dia (Manaus)", showgrid=True),
                        yaxis=dict(title="Temperatura (°C)", showgrid=True),
                        yaxis2=dict(title="Chuva (mm)", overlaying="y", side="right", showgrid=False),
                        legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"),
                        margin=dict(t=60, b=50, l=60, r=60),
                        template="plotly_white", height=440
                    )
                    figw.update_xaxes(dtick="D1", tickformat="%d/%m")
                    graph_week_combo = figw.to_html(full_html=False, include_plotlyjs="cdn")
        except Exception as e:
            _dbg(f"ERRO semanal: {e}")

        # Mensal
        graph_month = '<div class="alert alert-info m-0">Sem dados para o mês.</div>'
        month_label = now.strftime("%m/%Y")
        month_tmax = month_tmin = month_rain_total = "—"
        month_rain_days = month_dry_days = 0
        month_tmax_day = month_tmin_day = "—"
        try:
            if isinstance(df_month, pd.DataFrame) and not df_month.empty:
                m = df_month[(df_month.index.date >= month_start) & (df_month.index.date <= month_end_for_axis)]
                have_rain_m = "CHUVA" in m.columns
                agg = {"TEM_INS": ["min","mean","max"]}
                if have_rain_m: agg["CHUVA"] = "sum"
                monthly = m.groupby(m.index.normalize()).agg(agg)
                cols = []
                for a, b in monthly.columns:
                    if a == "TEM_INS" and b == "min":  cols.append("TEMP_min")
                    elif a == "TEM_INS" and b == "mean": cols.append("TEMP_mean")
                    elif a == "TEM_INS" and b == "max":  cols.append("TEMP_max")
                    elif a == "CHUVA" and b == "sum":   cols.append("CHUVA_sum")
                monthly.columns = cols
                x_days = pd.date_range(
                    start=pd.Timestamp(month_start, tz=TZ_AM),
                    end=pd.Timestamp(month_end_for_axis, tz=TZ_AM),
                    freq="D"
                )
                monthly_full = monthly.reindex(x_days)
                if "CHUVA_sum" in monthly_full.columns:
                    monthly_full["CHUVA_sum"] = monthly_full["CHUVA_sum"].fillna(0)
                if "TEMP_max" in monthly.columns and monthly["TEMP_max"].notna().any():
                    tmax_val = float(monthly["TEMP_max"].max()); month_tmax = f"{tmax_val:.1f}"
                    month_tmax_day = pd.Timestamp(monthly["TEMP_max"].astype(float).idxmax()).strftime("%d/%m")
                if "TEMP_min" in monthly.columns and monthly["TEMP_min"].notna().any():
                    tmin_val = float(monthly["TEMP_min"].min()); month_tmin = f"{tmin_val:.1f}"
                    month_tmin_day = pd.Timestamp(monthly["TEMP_min"].astype(float).idxmin()).strftime("%d/%m")
                if "CHUVA_sum" in monthly_full.columns:
                    month_rain_total = f"{float(monthly_full['CHUVA_sum'].sum()):.1f}"
                    month_rain_days = int((monthly_full["CHUVA_sum"] > 0).sum())
                    month_dry_days  = int((monthly_full["CHUVA_sum"] <= 0).sum())
                fig_m = go.Figure()
                if "CHUVA_sum" in monthly_full.columns:
                    fig_m.add_trace(go.Bar(x=x_days, y=monthly_full["CHUVA_sum"],
                                           name="Chuva diária (mm)", opacity=0.6, marker_line_width=0, yaxis="y2"))
                if "TEMP_mean" in monthly_full.columns:
                    fig_m.add_trace(go.Scatter(x=x_days, y=monthly_full["TEMP_mean"],
                                               name="Temperatura média (°C)", mode="lines+markers", line=dict(width=2)))
                if "TEMP_max" in monthly_full.columns:
                    fig_m.add_trace(go.Scatter(x=x_days, y=monthly_full["TEMP_max"],
                                               name="Temperatura máx (°C)", mode="lines+markers"))
                if "TEMP_min" in monthly_full.columns:
                    fig_m.add_trace(go.Scatter(x=x_days, y=monthly_full["TEMP_min"],
                                               name="Temperatura mín (°C)", mode="lines+markers"))
                fig_m.update_layout(
                    title=f"Mensal — {month_label} (Hora Manaus)",
                    xaxis=dict(title=f"Dia do mês (1..{month_end_for_axis.day})", showgrid=True),
                    yaxis=dict(title="Temperatura (°C)", showgrid=True),
                    yaxis2=dict(title="Chuva (mm)", overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"),
                    margin=dict(t=60, b=50, l=60, r=60),
                    template="plotly_white", height=440
                )
                month_range_start = pd.Timestamp(month_start, tz=TZ_AM)
                month_range_end   = pd.Timestamp(month_end_for_axis, tz=TZ_AM) + pd.Timedelta(hours=23, minutes=59, seconds=59)
                fig_m.update_xaxes(range=[month_range_start, month_range_end], dtick="D1", tickformat="%d/%m")
                graph_month = fig_m.to_html(full_html=False, include_plotlyjs="cdn")
        except Exception as e:
            _dbg(f"ERRO mensal: {e}")

        # Climatologia
        graph_clima_tmax = graph_clima_tmed = graph_clima_tmin = graph_clima_prec = '<div class="alert alert-info m-0">Sem climatologia.</div>'
        clima_periodo = "1931–1960 · 1961–1990 · 1991–2020"
        try:
            df_tmax = _df_from_csv_any("temp_maxima.csv")
            df_tmed = _df_from_csv_any("temp_media.csv")
            df_tmin = _df_from_csv_any("temp_minima.csv")
            df_prec = _df_from_csv_any("Precipitacao_acumulada.csv")
            graph_clima_tmax = _plot_line_periodos(df_tmax, ylab="°C") if {"mes","periodo","valor"}.issubset(df_tmax.columns) else _plot_line_simple(df_tmax, ylab="°C")
            graph_clima_tmed = _plot_line_periodos(df_tmed, ylab="°C") if {"mes","periodo","valor"}.issubset(df_tmed.columns) else _plot_line_simple(df_tmed, ylab="°C")
            graph_clima_tmin = _plot_line_periodos(df_tmin, ylab="°C") if {"mes","periodo","valor"}.issubset(df_tmin.columns) else _plot_line_simple(df_tmin, ylab="°C")
            graph_clima_prec = _plot_bar_periodos(df_prec,  ylab="mm")  if {"mes","periodo","valor"}.issubset(df_prec.columns) else _plot_bar_simple(df_prec,  ylab="mm")
        except Exception as e:
            _dbg(f"ERRO climatologia: {e}")

        # Alertas
        geojson_str, alert_first, alert_error = build_alert_fc(tempo_key="hoje")

        ctx = {
            "station": station,
            "station_name": station_name,
            "station_lat": station_lat,
            "station_lon": station_lon,
            "update_time": update_time,
            "update_date": update_date,
            # tempo real
            "rt_temp_value": rt_temp_value,
            "rt_feels_value": rt_feels_value,
            "rt_humi_value": rt_humi_value,
            "rt_pres_value": rt_pres_value,
            "rt_wind_value": rt_wind_value,
            "rt_insol_value": rt_insol_value,
            # diário
            "pill_diario": pill_diario,
            "graph_daily": graph_daily,
            # semanal
            "week_tmax": week_tmax, "week_tmax_day": week_tmax_day,
            "week_tmin": week_tmin, "week_tmin_day": week_tmin_day,
            "week_temp_avg": week_temp_avg,
            "week_rain_total": week_rain_total,
            "week_rain_days": week_rain_days,
            "week_dry_days": week_dry_days,
            "graph_week_combo": graph_week_combo,
            # mensal
            "month_label": month_label,
            "month_tmax": month_tmax, "month_tmax_day": month_tmax_day,
            "month_tmin": month_tmin, "month_tmin_day": month_tmin_day,
            "month_rain_total": month_rain_total,
            "month_rain_days": month_rain_days,
            "month_dry_days": month_dry_days,
            "graph_month": graph_month,
            # climatologia
            "clima_periodo": clima_periodo,
            "graph_clima_tmax": graph_clima_tmax,
            "graph_clima_tmed": graph_clima_tmed,
            "graph_clima_tmin": graph_clima_tmin,
            "graph_clima_prec": graph_clima_prec,
            # alertas
            "geojson_str": geojson_str,
            "alert_selected": json.dumps(alert_first or None, ensure_ascii=False),
            "alert_error": alert_error,
            # ui
            "active_tab": tab,
            "error_message": api_error,
        }
        cache.set(cache_key, ctx, timeout=900)
    ctx["active_tab"] = tab
    return render(request, "siteapp/inmet_painel.html", ctx)

# =============================================================================
# ZEUS — Assistente IA (escopo LabInstru/Meteorologia)
# =============================================================================

def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = re.sub(r"[\u0300-\u036f]", "", s)
    return s

def _is_lab_or_meteo(q: str) -> bool:
    qn = _norm(q)
    termos = [
        # LabInstru / site
        "labinstru","site","pagina","página","aba","uea","quem somos","estacao","estação",
        "rede hobo","tempo agora","satelite","satélite","radar","estagio","estágio",
        "projetos","iniciacao","iniciação","extensao","extensão","eventos","contato",
        # Meteorologia geral
        "meteorologia","chuva","precipitacao","precipitação","temperatura","umidade","vento",
        "frente fria","conveccao","convecção","zcas","zcit","el nino","el niño","la nina",
        "enso","seca","enchente","manaus","amazonia","índice de calor","indice de calor",
        "disdrometro","disdrômetro","noaa","cptec","inmet","wmo"
    ]
    return any(t in qn for t in termos)

def _human_refusal(_: str) -> str:
    return (
        "Desculpa, eu só consigo ajudar com **assuntos do LabInstru e de meteorologia**. "
        "Posso responder, por exemplo: *Quais abas existem no site?*, "
        "*Onde vejo os dados da estação?* ou *Explique El Niño em Manaus* 🙂"
    )

KB_ITENS = [
    {"gatilhos": ["quem somos","equipe","sobre"],
     "resposta": "A aba **Quem somos** apresenta o laboratório, sua missão e a equipe do LabInstru na UEA."},
    {"gatilhos": ["estacao","estação","dados ao vivo","temperatura agora","estacao da est"],
     "resposta": "Na **Estação da EST** você acompanha dados ao vivo (temperatura, umidade, vento etc.)."},
    {"gatilhos": ["rede hobo","hobo"],
     "resposta": "A **Rede de estações HOBO** reúne informações e dados das estações automáticas do LabInstru."},
    {"gatilhos": ["tempo agora","condicoes","condições"],
     "resposta": "Em **O tempo agora** há um resumo das condições atuais para consulta rápida."},
    {"gatilhos": ["satelite","satélite","radar"],
     "resposta": "A aba **Satélite e radar** mostra imagens para acompanhar nuvens e precipitação."},
    {"gatilhos": ["estagio","estágio"],
     "resposta": "A seção **Estágio Curricular** traz orientações, critérios e passos para o estágio."},
    {"gatilhos": ["projetos","iniciacao","iniciação","extensao","extensão","eventos","vinculados"],
     "resposta": "Em **Projetos** há IC, Extensão, Eventos e Vinculados, com filtros por ano/área e busca."},
    {"gatilhos": ["contato","email","telefone","endereco","endereço"],
     "resposta": "Use a aba **Contato** para falar com a equipe do LabInstru pelos canais oficiais."},
]

def _tenta_faq(q: str):
    qn = _norm(q)
    best, score = None, 0
    for item in KB_ITENS:
        s = sum(1 for g in item["gatilhos"] if g in qn)
        if s > score:
            score, best = s, item
    return best["resposta"] if best and score > 0 else None

ALLOWED_DOMAINS = {
    "inmet.gov.br", "cptec.inpe.br", "tempo.cptec.inpe.br", "satelite.cptec.inpe.br",
    "noaa.gov", "wmo.int", "metoffice.gov.uk", "smn.gob.ar",
    "uea.edu.br", "ufam.edu.br", "fapeam.am.gov.br", "ana.gov.br", "gov.br",
}
PREFERRED_DOMAINS = ["cptec.inpe.br", "inmet.gov.br"]

def _netloc_allowed(netloc: str) -> bool:
    netloc = (netloc or "").lower()
    for d in ALLOWED_DOMAINS:
        if netloc == d or netloc.endswith("." + d):
            return True
    return False

def _domain_allowed(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc
        return _netloc_allowed(netloc)
    except Exception:
        return False

HEADERS = {
    "User-Agent": "LabInstru-ZEUS/1.1 (+https://labinstru.uea.edu.br)",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def _html_to_text(content: bytes) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content or b"", "lxml")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        txt = soup.get_text(separator=" ")
        return re.sub(r"\s+", " ", txt).strip()[:4000]
    except Exception:
        txt = re.sub(rb"<[^>]+>", b" ", content or b"", flags=re.S)
        return re.sub(r"\s+", " ", txt.decode(errors="ignore")).strip()[:4000]

def _pdf_to_text(content: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
        return (extract_text(io.BytesIO(content or b"")) or "").strip()[:4000]
    except Exception:
        return ""

def _fetch_text(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type","") or "").lower()
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            return _pdf_to_text(r.content)
        return _html_to_text(r.content)
    except Exception as e:
        logger.exception("Falha ao baixar fonte %s: %s", url, e)
        return ""

def _cse_keys():
    return (getattr(settings, "CSE_API_KEY", "") or "",
            getattr(settings, "CSE_CX", "") or "")

def _search_web(query: str, limit: int = 3):
    api_key, cx = _cse_keys()
    if not api_key or not cx:
        return []
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": limit}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in data.get("items", []) or []:
            link = it.get("link")
            if not link or not _domain_allowed(link):
                continue
            items.append({"title": it.get("title",""), "url": link, "mime": it.get("mime","")})
            if len(items) >= limit: break
        return items
    except Exception as e:
        logger.exception("Falha no CSE: %s", e)
        return []

def _search_web_domain(query: str, domain: str, limit: int = 2):
    api_key, cx = _cse_keys()
    if not api_key or not cx:
        return []
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": limit, "siteSearch": domain}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in data.get("items", []) or []:
            link = it.get("link")
            if not link or not _domain_allowed(link):
                continue
            items.append({"title": it.get("title",""), "url": link, "mime": it.get("mime","")})
            if len(items) >= limit: break
        return items
    except Exception as e:
        logger.exception("Falha no CSE (domínio %s): %s", domain, e)
        return []

_LOCAL_CACHE_TEXTS: dict[str, str] = {}

def _read_pdf_file(path: str) -> str:
    try:
        if path in _LOCAL_CACHE_TEXTS:
            return _LOCAL_CACHE_TEXTS[path]
        with open(path, "rb") as f:
            content = f.read()
        txt = _pdf_to_text(content)
        _LOCAL_CACHE_TEXTS[path] = txt
        return txt
    except Exception as e:
        logger.exception("Erro lendo PDF local %s: %s", path, e)
        return ""

def _local_context(max_chars_per: int = 1200) -> list[dict]:
    out = []
    sources = getattr(settings, "ZEUS_LOCAL_SOURCES", []) or []
    for src in sources:
        stype = (src.get("type") or "").lower()
        path = src.get("path")
        if stype == "pdf" and path:
            txt = _read_pdf_file(str(path))
            if txt:
                out.append({"title": src.get("title") or str(path), "url": f"file://{path}", "snippet": txt[:max_chars_per]})
    return out

def _dedup_by_url(items: list[dict]) -> list[dict]:
    seen, res = set(), []
    for it in items:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen.add(u); res.append(it)
    return res

def _collect_context(question: str, max_web_sources: int = 3):
    ctx = []
    local = _local_context(max_chars_per=1200)
    ctx.extend(local)
    for dom in PREFERRED_DOMAINS:
        ctx.extend(_search_web_domain(question, dom, limit=2))
    if max_web_sources > 0:
        web_so_far = len([c for c in ctx if not c["url"].startswith("file://")])
        remaining = max(0, max_web_sources - web_so_far)
        if remaining:
            ctx.extend(_search_web(question, limit=remaining))
    return _dedup_by_url(ctx)

def _prompt_with_context(q: str, ctx: list[dict]) -> str:
    linhas = [
        "Você é ZEUS, um assistente **humano e simpático** do LabInstru.",
        "Regras: 1) Responda apenas sobre LabInstru/meteorologia; 2) Use os trechos quando úteis; 3) Não invente; 4) 2–6 frases.",
        "", "Pergunta:", re.sub(r"\s+", " ", q).strip()[:400],
        "", "Contexto:"
    ]
    for i, c in enumerate(ctx, start=1):
        linhas.append(f"[{i}] {c['title']} — {c['url']}\nTrecho: {c.get('snippet','')}")
    linhas.append("\nSe usar alguma fonte, mencione 'Fontes: [1], [2]…' no final.")
    return "\n".join(linhas)

def _call_gemini(prompt: str) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    model   = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        return "Configuração do serviço de IA indisponível no momento."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 512}
    }
    try:
        r = requests.post(url, json=payload, headers={"Content-Type":"application/json"}, timeout=25)
        r.raise_for_status()
        data = r.json()
        txt = (data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "") or "").strip()
        return txt or "Não consegui gerar resposta agora."
    except Exception as e:
        logger.exception("Falha no Gemini: %s", e)
        return "Tive um erro ao consultar a IA neste momento."

@require_POST
def api_zeus(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        pergunta = (body.get("pergunta") or "").strip()
    except Exception:
        return JsonResponse({"resposta": "Não entendi sua pergunta."}, status=400)
    if not pergunta:
        return JsonResponse({"resposta": "Digite sua pergunta 🙂"})
    if len(pergunta) > 1000:
        pergunta = pergunta[:1000]
    if not _is_lab_or_meteo(pergunta):
        return JsonResponse({"resposta": _human_refusal(pergunta), "fontes": []})
    faq = _tenta_faq(pergunta)
    if faq:
        return JsonResponse({"resposta": f"{faq} Posso te guiar até lá se quiser. 🙂", "fontes": []})
    max_web = getattr(settings, "ZEUS_MAX_WEB_SOURCES", 3)
    context = _collect_context(pergunta, max_web_sources=max_web)
    prompt = _prompt_with_context(pergunta, context)
    resposta = _call_gemini(prompt)
    fontes = [{"titulo": c.get("title",""), "url": c.get("url","")} for c in context]
    if "não sei" in resposta.lower():
        resposta += "\n\nSe quiser, posso refinar a busca focando em outra palavra-chave. 😉"
    return JsonResponse({"resposta": resposta, "fontes": fontes})



