# siteapp/views.py
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # se quiser usar @csrf_exempt em algum endpoint
import os, io, base64, json
import requests
from datetime import datetime, timedelta, timezone, date

# ====== SUPABASE (hardcoded) ======
# Se não tiver a lib: pip install supabase
try:
    from supabase import create_client
except Exception:
    create_client = None

SUPABASE_URL = "https://pcrywykqioyzetdzxjae.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjcnl3eWtxaW95emV0ZHp4amFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NjE1MjYsImV4cCI6MjA2NzAzNzUyNn0.1kDyYzMnnmaV3SyS3_GmIlBgvOkBFifjmHlBj67pjnE"

# ===== HOME =====
def home(request):
    return render(request, 'siteapp/home.html')

# ===== QUEM SOMOS (equipe) =====
def quem_somos(request):
    equipe = [
        {"img": "equipe/maria_betania.jpg", "nome": "Profa. Maria Betânia Leal", "cargo": "Pesquisadora/Responsável", "lattes": "http://lattes.cnpq.br/6645179913028377"},
        {"img": "equipe/rodrigo_souza.jpg", "nome": "Prof. Rodrigo Souza", "cargo": "Pesquisador", "lattes": "http://lattes.cnpq.br/5622102962091766"},
        {"img": "equipe/rita_valeria.jpg", "nome": "Profa. Rita Valéria Andreoli", "cargo": "Pesquisadora", "lattes": "http://lattes.cnpq.br/5550289805439528"},
        {"img": "equipe/adriano_pedrosa.jpg", "nome": "Adriano Pedrosa", "cargo": "Bolsista PROTLAB-TRAINEE", "lattes": "http://lattes.cnpq.br/6377229544645237"},
        {"img": "equipe/lemoel_pimentel.jpg", "nome": "Lemoel Pimentel", "cargo": "Voluntário", "lattes": "http://lattes.cnpq.br/5593010828707685"},
        {"img": "equipe/nigia_nubia.jpg", "nome": "Nigia Núbia", "cargo": "Estagiária", "lattes": "http://lattes.cnpq.br/4303038702531746"},
        {"img": "equipe/abraao_soares.jpg", "nome": "Abraão Soares", "cargo": "Voluntário", "lattes": "http://lattes.cnpq.br/0216316050483380"},
    ]
    return render(request, 'siteapp/quem_somos.html', {"equipe": equipe})

# ===== DASHBOARD (placeholder) =====
def dashboard(request):
    return render(request, 'siteapp/dashboard.html')

# siteapp/views.py
import os
import json
import calendar
import numpy as np
import pandas as pd
import folium
from django.conf import settings
from django.shortcuts import render
from supabase import create_client
import plotly.graph_objects as go
from branca.element import MacroElement, Template


# ---------------------------------------------------------------------
# Utilitário: iterar coords de um GeoJSON (lon,lat) -> (lat,lon)
# ---------------------------------------------------------------------
def _iter_coords(obj):
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


# ---------------------------------------------------------------------
# View: Rede de Estações HOBO
# ---------------------------------------------------------------------
def rede_hobo(request):
    # ----------------------------- 1) Estações -----------------------------
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

    # rótulos completos para exibição
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

    # filtros (no momento, apenas Precipitação)
    variaveis = ["Precipitação"]
    variavel = request.GET.get("variavel", "Precipitação")
    estacao = request.GET.get("estacao", estacoes[0])
    try:
        ano = int(request.GET.get("ano", "2013"))
    except ValueError:
        ano = 2013

    # NOVO: escolha da escala da barra de cores
    # 'max' (padrão) usa o máximo real; 'p99' usa percentil 99 (robusto).
    escala = request.GET.get("escala", "max").lower()
    if escala not in {"max", "p99"}:
        escala = "max"

    # ------------------------ 2) Mapa Folium (travado) ------------------------
    manaus_lat, manaus_lon = -3.05, -59.96
    mapa = folium.Map(
        location=[manaus_lat, manaus_lon],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=False,   # remove botões "+/-"
    )

    # contorno de Manaus (static/geo/contorno_manaus.geojson)
    geojson_path = os.path.join(settings.BASE_DIR, "static", "geo", "contorno_manaus.geojson")
    with open(geojson_path, "r", encoding="utf-8") as f:
        manaus_geo = json.load(f)

    folium.GeoJson(
        manaus_geo, name="Contorno de Manaus",
        style_function=lambda _: {"fillColor": "#0000", "color": "#145DA0", "weight": 3, "fillOpacity": 0.0},
        tooltip="Município de Manaus", show=True
    ).add_to(mapa)

    # marcadores
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
    for lat, lon in _iter_coords(manaus_geo):
        lats.append(lat)
        lons.append(lon)
    mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20, 20))

    # trava interações no mapa
    lock_tpl = Template("""
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
    mlock = MacroElement()
    mlock._template = lock_tpl
    mapa.add_child(mlock)

    mapa_html = mapa._repr_html_()

    # --------------------- 3) Supabase -> Heatmap (chuva) ---------------------
    SUPABASE_URL = getattr(settings, "SUPABASE_URL",
                           os.environ.get("SUPABASE_URL", "https://pcrywykqioyzetdzxjae.supabase.co"))
    SUPABASE_KEY = getattr(settings, "SUPABASE_KEY",
                           os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjcnl3eWtxaW95emV0ZHp4amFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NjE1MjYsImV4cCI6MjA2NzAzNzUyNn0.1kDyYzMnnmaV3SyS3_GmIlBgvOkBFifjmHlBj67pjnE"))

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # código -> slug na tabela
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
                df, tabela_ok = tmp, nome
                break
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
        # coluna de valor
        col_val = "chuva_mm" if "chuva_mm" in df.columns else \
                  "precipitacao_mm" if "precipitacao_mm" in df.columns else \
                  "mm" if "mm" in df.columns else "valor"

        if col_val not in df.columns:
            grafico_html = (
                f"<div class='alert alert-warning'>Tabela <b>{tabela_ok}</b> sem coluna de valor "
                f"('chuva_mm', 'precipitacao_mm', 'mm' ou 'valor').</div>"
            )
        else:
            # prepara datas e índices
            df["data"] = pd.to_datetime(df["data"], errors="coerce")
            df = df.dropna(subset=["data"])
            df["mes"] = df["data"].dt.month
            df["dia"] = df["data"].dt.day

            # matriz 12x31 com NaN para dias sem dado
            mat = np.full((12, 31), np.nan)
            for _, r in df.iterrows():
                m, d = int(r["mes"]), int(r["dia"])
                if 1 <= m <= 12 and 1 <= d <= 31:
                    val = pd.to_numeric(r[col_val], errors="coerce")
                    mat[m - 1, d - 1] = float(val) if pd.notna(val) else np.nan

            # meses e dias
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                     'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            dias = list(range(1, 32))
            df_hm = pd.DataFrame(mat, index=meses, columns=dias)

            # --------- ESCALA DA BARRA (AJUSTE) ----------
            # Por padrão usa o máximo real; opcionalmente 'p99' para robustez.
            serie = pd.to_numeric(df[col_val], errors="coerce")
            serie_valid = serie[serie.notna() & np.isfinite(serie)]
            vmin = 0.0
            if not serie_valid.empty:
                if escala == "p99":
                    vmax = float(np.nanpercentile(serie_valid, 99))
                else:  # "max"
                    vmax = float(np.nanmax(serie_valid))
            else:
                vmax = 1.0
            if not np.isfinite(vmax) or vmax <= vmin:
                vmax = vmin + 1e-6
            # ---------------------------------------------

            # matriz de texto para hover (mostra dd/mm e valor)
            texto = np.empty_like(mat, dtype=object)
            for _, r in df.iterrows():
                m, d = int(r["mes"]), int(r["dia"])
                if 1 <= m <= 12 and 1 <= d <= 31:
                    val = pd.to_numeric(r[col_val], errors="coerce")
                    if pd.notna(val):
                        texto[m - 1, d - 1] = f"{d:02d}/{m:02d}/{ano} – {float(val):.2f} mm"
                    else:
                        texto[m - 1, d - 1] = "Sem dado"

            # heatmap
            fig = go.Figure(data=go.Heatmap(
                z=df_hm.values,
                x=df_hm.columns,
                y=df_hm.index,
                text=texto,
                hoverinfo="text",
                colorscale="YlGnBu",
                zmin=vmin,
                zmax=vmax,
                colorbar=dict(title="Precipitação (mm)"),
                hoverongaps=False,
                showscale=True,
                zsmooth=False
            ))

            # cinza para (a) dia inexistente no mês OU (b) célula NaN (sem dado)
            dias_por_mes = [calendar.monthrange(ano, m)[1] for m in range(1, 13)]
            for i in range(df_hm.shape[0]):
                for j in range(df_hm.shape[1]):
                    if j >= dias_por_mes[i] or np.isnan(df_hm.iloc[i, j]):
                        fig.add_shape(
                            type="rect",
                            x0=float(df_hm.columns[j]) - 0.5, x1=float(df_hm.columns[j]) + 0.5,
                            y0=i - 0.5, y1=i + 0.5,
                            fillcolor="lightgray",
                            line=dict(width=0),
                            layer="above"
                        )

            # eixo X com ticks 1..31
            fig.update_xaxes(
                tickmode="array",
                tickvals=dias,
                ticktext=[str(d) for d in dias],
                dtick=1,
                tickangle=0,
                ticks="outside",
                ticklen=3
            )

            nome_legivel_sel = label_por_estacao.get(estacao, estacao)
            fig.update_layout(
                template="plotly_white",
                title=f"Precipitação diária — {nome_legivel_sel} — {ano}",
                xaxis_title="Dia",
                yaxis_title="",
                autosize=True,
                height=650,
                margin=dict(l=80, r=30, t=90, b=60),
                font=dict(size=13)
            )

            grafico_html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                config={"displaylogo": False, "responsive": True}
            )

    # ----------------------------- 4) Render -----------------------------
    return render(request, "siteapp/rede_de_estacoes_hobo.html", {
        "mapa_html": mapa_html,
        "grafico_html": grafico_html,
        "variaveis": variaveis,          # apenas "Precipitação" (para o form)
        "variavel": variavel,
        "opcoes_estacoes": opcoes_estacoes,
        "estacao": estacao,
        "ano": ano,
        "escala": escala,                # 'max' (padrão) ou 'p99'
    })





# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils._os import safe_join

from django.contrib.staticfiles import finders  # localizar arquivos em static/

import os, json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import folium
from folium import Map, Marker, TileLayer
from folium.features import DivIcon
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from branca.element import MacroElement, Element
from jinja2 import Template

import requests

# ========= CONFIG =========
VIEW_CENTER = (-3.11, -60.02)
VIEW_ZOOM   = 11
MAP_H_PX    = 720
TZ          = "America/Manaus"

# BBox PurpleAir (Manaus)
MANAUS_BOUNDS = {"nwlng": -60.30, "nwlat": -2.90, "selng": -59.70, "selat": -3.35}

PURPLEAIR_API_KEY = "D949FBD6-5C4D-11F0-81BE-42010A80001F"
LOGO_URL = "/static/img/selva.png"

# Pastas
MEDIA_MAPS_DIR  = os.path.join(settings.MEDIA_ROOT, "maps")
MEDIA_CACHE_DIR = os.path.join(settings.MEDIA_ROOT, "cache")
os.makedirs(MEDIA_MAPS_DIR,  exist_ok=True)
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

# ========= MUNICÍPIOS RMM (13) =========
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

# ========= COLORMAPS =========
TEMP_STOPS_18UP = [(18,'#73e5a3'), (20,'#90eb9d'), (30,'#f9d057'), (40,'#d7191c')]
TEMP_CMAP = LinearColormap(
    colors=[c for _, c in TEMP_STOPS_18UP],
    index=[v for v,_ in TEMP_STOPS_18UP], vmin=18, vmax=40
)
TEMP_CMAP.caption = "Temperatura do Ar (°C) – Simple correction (PurpleAir −8 °F)"

# PM2.5 bins (CONAMA)
PM_BINS = [
    ("0–24.9",   "#39e639", "Boa"),
    ("25–49.9",  "#ffff00", "Moderada"),
    ("50–74.9",  "#f4a460", "Ruim"),
    ("75–124.9", "#ff3333", "Muito Ruim"),
    ("≥ 125",    "#a633cc", "Péssima"),
]

# ========= LOGO =========
class LogoTopRight(MacroElement):
    _template = Template("""
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

# ========= UTILS =========
def _ts_manaus(epoch):
    if epoch is None: return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=ZoneInfo("UTC")).astimezone(ZoneInfo(TZ))
    except Exception:
        return None

def _f_to_c(f): return (float(f) - 32.0) * 5/9
def _corr_selva_c(f):      return _f_to_c(f) - 2.0
def _corr_pa_simple_c(f):  return _f_to_c(float(f) - 8.0)  # Simple correction (−8 °F)

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

# ========= POPUPS =========
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

# ========= CACHE =========
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

# ========= PurpleAir (cache 10 min) =========
PA_TTL = 600

def _get_purpleair():
    cache = _read_cache("purpleair.json")
    now = datetime.now(ZoneInfo(TZ))
    ts  = cache.get("_ts")
    if ts:
        try:
            if (now - datetime.fromisoformat(ts)).total_seconds() <= PA_TTL:
                return cache.get("data", [])
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

# ========= Open-Meteo em lote (cache 10 min) =========
OM_TTL = 600
PRIMARY_MODEL = "ecmwf_ifs"

def _get_openmeteo_batch_rmm():
    """Lista na ordem dos MUNICIPIOS: dict(t2, rh, rain, iso)."""
    cache = _read_cache("openmeteo_rmm.json")
    now = datetime.now(ZoneInfo(TZ))
    ts  = cache.get("_ts")
    if ts:
        try:
            if (now - datetime.fromisoformat(ts)).total_seconds() <= OM_TTL:
                return cache.get("data", [])
        except Exception:
            pass

    lat_list = [it["lat"] for it in MUNICIPIOS]
    lon_list = [it["lon"] for it in MUNICIPIOS]
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
            "latitude": lat_list,
            "longitude": lon_list,
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
                iso = datetime.fromtimestamp(t_loc, ZoneInfo(TZ)).isoformat()
            data.append({"t2": t2, "rh": rh, "rain": rr, "iso": iso})
    except Exception:
        # Fallback JSON (1 chamada por município)
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

# ========= helpers arquivo/iframe =========
def _save_map(m, filename):
    os.makedirs(MEDIA_MAPS_DIR, exist_ok=True)
    path = os.path.join(MEDIA_MAPS_DIR, filename)
    m.save(path)
    return f"/embed/maps/{filename}"

# ========= Banner & ferramentas GeoJSON =========
def _banner(m: Map, text: str, pos="topright", color="#b91c1c"):
    html = f"""
    <div style="position:fixed;z-index:9999;{ 'top:14px;right:14px' if pos=='topright' else 'bottom:14px;left:14px' };
                background:rgba(255,255,255,.95);border-left:4px solid {color};
                padding:10px 12px;border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,.25);
                font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:520px;">
      <div style="font-weight:700;margin-bottom:4px;">Aviso</div>
      <div style="font-size:13px;line-height:1.35">{text}</div>
    </div>
    """
    m.get_root().html.add_child(Element(html))

def _find_static_geo(relpath: str) -> tuple[str | None, list]:
    """Procura o arquivo em múltiplos lugares. Retorna (caminho_encontrado, lista_tentativas)."""
    tried = []
    # 1) finders (STATICFILES_DIRS/apps)
    p = finders.find(f"geo/{relpath}")
    tried.append(p or f"[finders] geo/{relpath}")
    if p and os.path.exists(p): return p, tried

    # 2) BASE_DIR e variações
    base = settings.BASE_DIR
    parent = os.path.dirname(base)

    candidates = [
        os.path.join(base,   "static", "geo", relpath),
        os.path.join(base,   "labinstru_site", "static", "geo", relpath),
        os.path.join(parent, "static", "geo", relpath),
        os.path.join(parent, "labinstru_site", "static", "geo", relpath),
    ]
    for c in candidates:
        tried.append(c)
        if os.path.exists(c):
            return c, tried
    return None, tried

def _geojson_bounds(gj: dict):
    try:
        def _coords_iter(geom):
            t = geom.get("type")
            cs = geom.get("coordinates", [])
            if t == "Point":
                yield cs
            elif t == "LineString":
                for xy in cs: yield xy
            elif t == "Polygon":
                for ring in cs:
                    for xy in ring: yield xy
            elif t == "MultiPolygon":
                for poly in cs:
                    for ring in poly:
                        for xy in ring: yield xy
        xs, ys = [], []
        if gj.get("type") == "FeatureCollection":
            for ft in gj.get("features", []):
                geom = ft.get("geometry") or {}
                for lon, lat in _coords_iter(geom):
                    xs.append(float(lon)); ys.append(float(lat))
        elif gj.get("type") == "Feature":
            geom = gj.get("geometry") or {}
            for lon, lat in _coords_iter(geom):
                xs.append(float(lon)); ys.append(float(lat))
        else:
            for lon, lat in _coords_iter(gj):
                xs.append(float(lon)); ys.append(float(lat))
        if not xs or not ys: return None
        west, east = min(xs), max(xs)
        south, north = min(ys), max(ys)
        return [[south, west], [north, east]], (west, south, east, north)
    except Exception:
        return None

# ========= contorno padrão dos outros mapas (opcional) =========
def _load_manaus_geojson():
    path, _ = _find_static_geo("contorno_manaus.geojson")
    if not path: return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _add_contorno_manaus(m: Map):
    gj = _load_manaus_geojson()
    if not gj: return
    folium.GeoJson(
        gj,
        name="Contorno de Manaus",
        style_function=lambda _:
            {"fillColor": "#00000000", "color": "#145DA0", "weight": 3, "fillOpacity": 0.0},
        tooltip="Município de Manaus",
        show=True, control=False
    ).add_to(m)

# ========= Mun_Manaus.geojson (MESMO estilo + diagnóstico) =========
def _add_mun_manaus_mesmo_estilo(m: Map):
    path, tried = _find_static_geo("Mun_Manaus.geojson")
    if not path:
        lista = "<br>".join(f"<code>{t}</code>" for t in tried)
        _banner(
            m,
            "Não encontrei <b>Mun_Manaus.geojson</b> nos caminhos testados:<br>" + lista +
            "<br>Coloque o arquivo em <code>labinstru_site/static/geo/</code> ou <code>static/geo/</code>.",
            "topright", "#b45309"
        )
        return

    # Lê e valida
    try:
        with open(path, "r", encoding="utf-8") as f:
            gj = json.load(f)
    except Exception as e:
        _banner(m, f"Erro lendo <code>{path}</code>: {e}", "topright", "#b91c1c")
        return

    if not isinstance(gj, dict) or gj.get("type") not in ("FeatureCollection", "Feature"):
        _banner(m, f"<code>{os.path.basename(path)}</code> não é GeoJSON válido (Feature/FeatureCollection).", "topright", "#b91c1c")
        return

    # Bounds + checagem de projeção (valores fora do range típico WGS84)
    bb = _geojson_bounds(gj)
    if bb:
        bounds, (w,s,e,n) = bb
        if any(abs(v) > 200 for v in (w,s,e,n)):
            _banner(
                m,
                f"O arquivo parece estar em UTM/projeção não-WGS84 (bounds: W={w}, S={s}, E={e}, N={n}). "
                "Reprojete para EPSG:4326 (WGS84).",
                "topright", "#b91c1c"
            )
        else:
            try:
                m.fit_bounds(bounds, padding=(12, 12))
            except Exception:
                pass

    # Desenha com o MESMO estilo azul dos outros mapas
    folium.GeoJson(
        gj,
        name="Município de Manaus",
        style_function=lambda _:
            {"fillColor": "#00000000", "color": "#145DA0", "weight": 3, "fillOpacity": 0.0},
        tooltip="Município de Manaus",
        show=True, control=False
    ).add_to(m)

    # Selo informando de onde veio
    m.get_root().html.add_child(Element(
        f"<div style='position:fixed;z-index:9999;bottom:14px;right:14px;"
        f"background:rgba(255,255,255,.9);padding:6px 10px;border-radius:10px;"
        f"box-shadow:0 4px 12px rgba(0,0,0,.2);font:12px/1.2 system-ui,Segoe UI,Arial'>"
        f"Mun_Manaus: <b>{path}</b></div>"
    ))

# ========= Legendas =========
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

# ========= Mapas =========
def _map_temperatura_real():
    sensors = _get_purpleair()
    m = Map(location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM,
            tiles=None, control_scale=True, prefer_canvas=True, zoom_control=True)
    TileLayer('OpenStreetMap', control=False).add_to(m)
    Fullscreen(position="topleft", force_separate_button=True).add_to(m)
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

def _map_qualidade_ar():
    sensors = _get_purpleair()
    m = Map(location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM,
            tiles=None, control_scale=True, prefer_canvas=True, zoom_control=True)
    TileLayer('OpenStreetMap', control=False).add_to(m)
    Fullscreen(position="topleft", force_separate_button=True).add_to(m)
    m.add_child(LogoTopRight(LOGO_URL, width=160, margin=10, opacity=1.0))
    _add_contorno_manaus(m)

    for s in sensors:
        pm = s.get("pm")
        if pm is None:
            continue
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

def _map_estacoes_virtuais():
    lote = _get_openmeteo_batch_rmm()
    m = Map(location=[-3.2, -60.0], zoom_start=8,
            tiles=None, control_scale=True, prefer_canvas=True)
    TileLayer('OpenStreetMap', control=False).add_to(m)
    Fullscreen(position="topleft", force_separate_button=True).add_to(m)
    m.add_child(LogoTopRight(LOGO_URL, width=160, margin=10, opacity=1.0))

    # Contorno AZUL idêntico aos outros mapas, a partir de Mun_Manaus.geojson (com diagnóstico)
    _add_mun_manaus_mesmo_estilo(m)

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

    # Enquadramento geral adicional
    try:
        lats = [it["lat"] for it in MUNICIPIOS]; lons = [it["lon"] for it in MUNICIPIOS]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(10, 10))
    except Exception:
        pass

    _add_legend_temp(m)
    return _save_map(m, "mapa_virtuais_rmm.html")

# ========= VIEWS =========
def condicoes_atmosfera(request):
    temp_iframe = _map_temperatura_real()
    ar_iframe   = _map_qualidade_ar()
    virt_iframe = _map_estacoes_virtuais()
    ctx = {
        "mapa_temp_iframe": temp_iframe,
        "mapa_ar_iframe":   ar_iframe,
        "mapa_virt_iframe": virt_iframe,
        "map_height": MAP_H_PX,
        "proxima": (datetime.now(ZoneInfo(TZ)) + timedelta(minutes=10)).strftime("%H:%M"),
        "temp_cmap_json": json.dumps(TEMP_STOPS_18UP),
    }
    return render(request, "siteapp/condicoes.html", ctx)

@xframe_options_exempt
def embed_map(request, fname):
    """Serve /media/maps/<fname> como text/html, liberado para <iframe>."""
    base = os.path.join(settings.MEDIA_ROOT, "maps")
    try:
        path = safe_join(base, fname)
    except Exception:
        raise Http404()
    if not os.path.exists(path):
        raise Http404()
    return FileResponse(open(path, "rb"), content_type="text/html")


















# ===== SATÉLITE E RADAR (iframes) =====
def satelite_radar(request):
    return render(request, 'siteapp/satelite_radar.html', {
        "agora": datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
    })



from django.shortcuts import render

def estagio(request):
    estagiarios = [
        {"nome": "Rodrigo da Cruz França", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "13/04/2016 a 30/08/2016"},
        {"nome": "Daniela Correa Chaves", "curso": "Engenharia Ambiental (Fametro)", "area": "Instrumentação Meteorológica", "periodo": "11/09/2017 a 15/11/2017"},
        {"nome": "Katharina de Carvalho Capobiango", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "21/03/2019 a 28/06/2019"},
        {"nome": "Lemoel Pimentel de Brito", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "06/12/2022 a 15/08/2023"},
        {"nome": "Sarah Regina Oliveira de Sousa", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "01/02/2024 a 19/07/2024"},
        {"nome": "Nigia Núbia Santos Silva", "curso": "Graduação em Meteorologia (UEA)", "area": "Instrumentação Meteorológica", "periodo": "19/05/2025 a atual"},
    ]
    # Marca quem está no período atual
    for e in estagiarios:
        e["atual"] = "atual" in e["periodo"].lower()
    return render(request, "siteapp/estagio.html", {"estagiarios": estagiarios})





# ===== PROJETOS =====
def projetos(request):
    return render(request, 'siteapp/projetos.html')







# ===== EVENTOS (placeholder) =====
def eventos(request):
    return render(request, 'siteapp/eventos.html')






# siteapp/views.py
import os, socket
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection, BadHeaderError

# ================== CONFIG ==================
SENDER_NAME  = "LabInstru"
SENDER_EMAIL = "alp.mcl23@uea.edu.br"          # Remetente fixo
TO_EMAIL     = "mloliveira@uea.edu.br"          # Destinatário fixo (tudo vai para este e-mail)

# Senha de app (16 caracteres) que você forneceu, sem espaços:
GMAIL_APP_PASSWORD = "oybyxdorpmtsqehf"

FROM_EMAIL_FMT = f"{SENDER_NAME} <{SENDER_EMAIL}>"
TO_LIST        = [TO_EMAIL]

def _fmt_err(e):
    eno = getattr(e, "errno", None)
    if isinstance(e, (socket.error, OSError)):
        return f"{e.__class__.__name__} (errno={eno}) {e}"
    return f"{e.__class__.__name__}: {e}"

def _enviar_gmail(subject: str, body: str, reply_to_email: str | None):
    """
    Envia via Gmail:
      1) SSL (porta 465)
      2) se falhar, TLS (porta 587)
    Requer 2FA ativo e senha de app válida para SENDER_EMAIL.
    """
    if not GMAIL_APP_PASSWORD or len(GMAIL_APP_PASSWORD) != 16:
        return False, "Senha de app inválida (precisa ter 16 caracteres)."

    # 1) SSL 465
    try:
        conn_ssl = get_connection(
            host="smtp.gmail.com",
            port=465,
            username=SENDER_EMAIL,
            password=GMAIL_APP_PASSWORD,
            use_ssl=True,
            timeout=20,
        )
        EmailMessage(
            subject=subject,
            body=body,
            from_email=FROM_EMAIL_FMT,
            to=TO_LIST,
            reply_to=[reply_to_email] if reply_to_email else None,
            connection=conn_ssl,
        ).send()
        return True, "via Gmail SSL 465"
    except Exception as e_ssl:
        err_ssl = e_ssl

    # 2) TLS 587
    try:
        conn_tls = get_connection(
            host="smtp.gmail.com",
            port=587,
            username=SENDER_EMAIL,
            password=GMAIL_APP_PASSWORD,
            use_tls=True,
            timeout=20,
        )
        EmailMessage(
            subject=subject,
            body=body,
            from_email=FROM_EMAIL_FMT,
            to=TO_LIST,
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

        # Validação simples
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




import calendar
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from django.shortcuts import render
from django.core.cache import cache
from zoneinfo import ZoneInfo

TZ_AM = ZoneInfo("America/Manaus")

INMET_TOKEN = "OVVKV3hMSjVWWGtVYm5wMGFsaVc1VXhteEYwY1cwSDI=9UJWxLJ5VXkUbnp0aliW5UxmxF0cW0H2"  # troque se necessário

def _dbg(msg):  # prints simples para log de servidor
    print(f"[INMET] {msg}")

def get_station_data(station, start_date, end_date):
    """
    Busca dados no INMET e retorna DataFrame com índice no fuso America/Manaus.
    Nunca lança exceção para cima: retorna (df|None, msg_erro|None).
    """
    url = f"https://apitempo.inmet.gov.br/token/estacao/{start_date}/{end_date}/{station}/{INMET_TOKEN}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, "Sem dados (API retornou lista vazia)."

        df = pd.DataFrame(data)

        # Garantir colunas esperadas, mesmo se vierem ausentes
        for col in ['TEM_INS', 'UMD_INS', 'PRE_INS', 'VEN_VEL', 'CHUVA', 'PTO_INS']:
            if col not in df.columns:
                df[col] = pd.NA
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Datetime UTC -> Manaus
        dt = pd.to_datetime(
            df['DT_MEDICAO'].astype(str) + ' ' + df['HR_MEDICAO'].astype(str).str.zfill(4),
            format='%Y-%m-%d %H%M', errors='coerce'
        )
        ok = dt.notna()
        if not ok.any():
            return None, "Falha ao interpretar data/hora."
        df = df.loc[ok].copy()
        df.index = dt[ok].dt.tz_localize("UTC").dt.tz_convert(TZ_AM)
        df.sort_index(inplace=True)
        return df, None

    except Exception as e:
        return None, f"Erro ao buscar API: {e}"

def inmet_painel(request, station='A101'):
    """
    Painel completo com FALLOVER: sempre entrega HTML válido nos gráficos,
    mesmo se houver pouco dado ou dia sem medição.
    """
    cache_key = f"inmet_data_v2_{station}"
    ctx = cache.get(cache_key)

    if ctx is None:
        now = datetime.now(TZ_AM)
        today = now.date()

        # --- Janelas ---
        week_start_api = (now - timedelta(days=8)).strftime('%Y-%m-%d')  # margem
        today_api = now.strftime('%Y-%m-%d')
        month_start_date = now.replace(day=1).date()
        month_last_day = calendar.monthrange(now.year, now.month)[1]
        month_end_date = datetime(now.year, now.month, month_last_day, tzinfo=TZ_AM).date()

        # --- Busca semana e mês (isoladas) ---
        df_week, err_w = get_station_data(station, week_start_api, today_api)
        df_month_all, err_m = get_station_data(station, month_start_date.strftime('%Y-%m-%d'), today_api)

        # Se ambas falharam, ainda assim devolvemos gráficos vazios, não erro vermelho
        api_error = err_w or err_m

        # ===================== PÍLULA TEMPO REAL =====================
        temp_current = umid_current = chuva_current = '-'
        update_time = 'Dados indisponíveis'
        if isinstance(df_week, pd.DataFrame) and not df_week.empty:
            valid = df_week.dropna(subset=['TEM_INS'])
            if not valid.empty:
                last = valid.iloc[-1]
                update_time = last.name.strftime('%H:%M de %d/%m/%Y')
                temp_current = f"{last.get('TEM_INS'):.1f}" if pd.notna(last.get('TEM_INS')) else '-'
                umid_current = f"{last.get('UMD_INS'):.1f}" if pd.notna(last.get('UMD_INS')) else '-'
                chuva_current = f"{last.get('CHUVA'):.1f}" if pd.notna(last.get('CHUVA')) else '-'

        # ===================== RESUMO DO DIA + GRÁFICO DIÁRIO =====================
        graph_daily = '<div class="alert alert-info m-0">Sem dados do dia.</div>'
        pill_diario = "Sem dados para o dia."
        try:
            base = df_week if isinstance(df_week, pd.DataFrame) else None
            if base is not None and not base.empty:
                last_day = base.index.max().date()
                df_today = base[base.index.date == last_day].copy()
                if not df_today.empty:
                    # Pílula
                    if df_today['TEM_INS'].notna().any():
                        tmin = df_today['TEM_INS'].min()
                        tmax = df_today['TEM_INS'].max()
                    else:
                        tmin = tmax = pd.NA
                    ch = df_today['CHUVA'].sum(min_count=1)
                    pill_diario = f"Mín {tmin:.1f} °C · Máx {tmax:.1f} °C · Chuva {float(ch or 0):.1f} mm" if pd.notna(tmin) and pd.notna(tmax) else "Sem dados para o dia."

                    # Mesmo com buracos, plota eixos
                    fig = go.Figure()
                    # barra chuva
                    fig.add_trace(go.Bar(x=df_today.index, y=df_today['CHUVA'].fillna(0),
                                         name='Precipitação', opacity=0.55, marker_line_width=0, yaxis='y3'))
                    # umidade
                    fig.add_trace(go.Scatter(x=df_today.index, y=df_today['UMD_INS'],
                                             name='Umidade', mode='lines+markers', line=dict(dash='dot'), yaxis='y2'))
                    # temperatura e “sensação” (ponto de orvalho)
                    fig.add_trace(go.Scatter(x=df_today.index, y=df_today['TEM_INS'],
                                             name='Temperatura', mode='lines+markers', yaxis='y1'))
                    fig.add_trace(go.Scatter(x=df_today.index, y=df_today['PTO_INS'],
                                             name='Sensação térmica', mode='lines+markers', yaxis='y1'))

                    fig.update_layout(
                        title=f'Condições do Dia — {last_day.strftime("%d/%m/%Y")} (Hora Manaus)',
                        xaxis=dict(title='Horas (America/Manaus)', tickformat='%H:%M', showgrid=True),
                        yaxis=dict(title='Temperatura (°C)', showgrid=True, position=0.06),
                        yaxis2=dict(title='Umidade (%)', overlaying='y', side='right', range=[40,100], showgrid=False),
                        yaxis3=dict(title='Precipitação (mm)', overlaying='y', side='left', position=0.0, showgrid=False),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(t=60, b=50, l=60, r=60),
                        template="plotly_white",
                        height=420
                    )
                    graph_daily = fig.to_html(full_html=False, include_plotlyjs=False)
        except Exception as e:
            _dbg(f"ERRO gráfico diário: {e}")

        # ===================== SEMANA (EXATOS ÚLTIMOS 7 DIAS) =====================
        graph_temp_week = '<div class="alert alert-info m-0">Sem dados para os últimos 7 dias.</div>'
        graph_chuva_week = '<div class="alert alert-info m-0">Sem dados para os últimos 7 dias.</div>'
        pill_semana = "Sem dados na semana."
        try:
            end7 = today
            start7 = end7 - timedelta(days=6)
            idx7 = pd.date_range(start=pd.Timestamp(start7, tz=TZ_AM),
                                 end=pd.Timestamp(end7, tz=TZ_AM), freq='D')
            if isinstance(df_week, pd.DataFrame) and not df_week.empty:
                w = df_week[(df_week.index.date >= start7) & (df_week.index.date <= end7)].copy()
                weekly = w.resample('D').agg({'TEM_INS':['mean','max'], 'CHUVA':'sum'}).reindex(idx7)
                weekly.columns = ['_'.join(c) for c in weekly.columns.to_flat_index()]
                if 'CHUVA_sum' in weekly.columns:
                    weekly['CHUVA_sum'] = weekly['CHUVA_sum'].fillna(0)

                total_chuva_week = float(weekly.get('CHUVA_sum', pd.Series(dtype=float)).sum() or 0.0)
                mean_of_max = float(weekly.get('TEM_INS_max', pd.Series(dtype=float)).mean() or float('nan'))
                pill_semana = f"Média da Máx. {mean_of_max:.1f} °C · Chuva total {total_chuva_week:.1f} mm"

                # gráficos
                fig_wt = px.line(weekly, y='TEM_INS_mean', title='Temperatura Média — últimos 7 dias (°C)')
                fig_wt.update_layout(height=300, margin=dict(t=40,b=20,l=40,r=20), xaxis_title='', yaxis_title='Temp (°C)')
                graph_temp_week = fig_wt.to_html(full_html=False, include_plotlyjs=False)

                fig_wc = px.bar(weekly, y='CHUVA_sum', title='Chuva — últimos 7 dias (mm)')
                fig_wc.update_layout(height=300, margin=dict(t=40,b=20,l=40,r=20), xaxis_title='', yaxis_title='Chuva (mm)')
                graph_chuva_week = fig_wc.to_html(full_html=False, include_plotlyjs=False)
        except Exception as e:
            _dbg(f"ERRO semana: {e}")

        # ===================== MENSAL (1º → último dia do mês) =====================
        graph_month = '<div class="alert alert-info m-0">Sem dados para o mês.</div>'
        pill_mensal = "Sem dados para o mês."
        try:
            idx_month = pd.date_range(start=pd.Timestamp(month_start_date, tz=TZ_AM),
                                      end=pd.Timestamp(month_end_date, tz=TZ_AM), freq='D')
            if isinstance(df_month_all, pd.DataFrame) and not df_month_all.empty:
                # métricas até hoje
                m_metrics = df_month_all[(df_month_all.index.date >= month_start_date) &
                                         (df_month_all.index.date <= today)]
                monthly = m_metrics.resample('D').agg({
                    'TEM_INS':['min','mean','max'], 'CHUVA':'sum'
                })
                monthly.columns = ['TEMP_min','TEMP_mean','TEMP_max','CHUVA_sum']

                # para eixo completo do mês
                monthly_full = monthly.reindex(idx_month)
                monthly_full['CHUVA_sum'] = monthly_full['CHUVA_sum'].fillna(0)

                # pílula
                if not monthly.empty:
                    tmin = monthly['TEMP_min'].min()
                    tmin_day = monthly['TEMP_min'].idxmin()
                    tmax = monthly['TEMP_max'].max()
                    tmax_day = monthly['TEMP_max'].idxmax()
                    tmean = monthly['TEMP_mean'].mean()
                    rain_total = monthly['CHUVA_sum'].sum()
                    def _d(d): return d.strftime('%d/%m') if pd.notna(d) else '--/--'
                    pill_mensal = f"Média {tmean:.1f} °C · Máx {tmax:.1f} °C ({_d(tmax_day)}) · Mín {tmin:.1f} °C ({_d(tmin_day)}) · Chuva {rain_total:.1f} mm"

                # gráfico
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(x=monthly_full.index, y=monthly_full['CHUVA_sum'],
                                       name='Chuva diária (mm)', opacity=0.6, marker_line_width=0, yaxis='y2'))
                fig_m.add_trace(go.Scatter(x=monthly_full.index, y=monthly_full['TEMP_mean'],
                                           name='Temperatura média', mode='lines+markers', line=dict(width=2)))
                fig_m.add_trace(go.Scatter(x=monthly_full.index, y=monthly_full['TEMP_max'],
                                           name='Temperatura máx', mode='lines+markers'))
                fig_m.add_trace(go.Scatter(x=monthly_full.index, y=monthly_full['TEMP_min'],
                                           name='Temperatura mín', mode='lines+markers'))

                fig_m.update_layout(
                    title=f'Mensal — {now.strftime("%m/%Y")} (Hora Manaus)',
                    xaxis=dict(title='Dia do mês', dtick='D1', tickformat='%d', showgrid=True,
                               range=[pd.Timestamp(month_start_date, tz=TZ_AM), pd.Timestamp(month_end_date, tz=TZ_AM)]),
                    yaxis=dict(title='Temperatura (°C)', showgrid=True),
                    yaxis2=dict(title='Chuva (mm)', overlaying='y', side='right', showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=60,b=50,l=60,r=60),
                    template="plotly_white", height=420
                )
                graph_month = fig_m.to_html(full_html=False, include_plotlyjs=False)
        except Exception as e:
            _dbg(f"ERRO mensal: {e}")

        # ===================== CONTEXTO FINAL =====================
        ctx = {
            'station': station,
            'update_time': update_time,
            'temp_current': temp_current, 'umid_current': umid_current, 'chuva_current': chuva_current,
            'pill_diario': pill_diario, 'pill_semana': pill_semana, 'pill_mensal': pill_mensal,
            'pill_anual': '—', 'pill_clima': '—',
            'graph_daily': graph_daily,
            'graph_temp_week': graph_temp_week,
            'graph_chuva_week': graph_chuva_week,
            'graph_month': graph_month,
            'error_message': api_error,  # se quiser exibir discretamente no topo
        }
        cache.set(cache_key, ctx, timeout=1800)  # 30 min

    return render(request, 'siteapp/inmet_painel.html', ctx)















# siteapp/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
# Se for chamar via JS sem token CSRF, pode usar:
# from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import logging
import requests
import json
import re
import unicodedata
from urllib.parse import urlparse

# ==== Dependências sugeridas ====
# pip install requests beautifulsoup4 lxml pdfminer.six python-dotenv

logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Utilidades
# ------------------------------------------------------
def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = re.sub(r"[\u0300-\u036f]", "", s)
    return s

def _is_lab_or_meteo(q: str) -> bool:
    """Permite LabInstru e Meteorologia (Amazônia/Manaus etc.)."""
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

def _trim(txt: str, limit: int = 2000) -> str:
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]

# ------------------------------------------------------
# Mini-FAQ (LabInstru) – respostas rápidas sem chamar LLM
# ------------------------------------------------------
KB_ITENS = [
    {
        "gatilhos": ["quem somos","equipe","sobre"],
        "resposta": "A aba **Quem somos** apresenta o laboratório, sua missão e a equipe do LabInstru na UEA."
    },
    {
        "gatilhos": ["estacao","estação","dados ao vivo","temperatura agora","estacao da est"],
        "resposta": "Na **Estação da EST** você acompanha dados ao vivo (temperatura, umidade, vento etc.)."
    },
    {
        "gatilhos": ["rede hobo","hobo"],
        "resposta": "A **Rede de estações HOBO** reúne informações e dados das estações automáticas do LabInstru."
    },
    {
        "gatilhos": ["tempo agora","condicoes","condições"],
        "resposta": "Em **O tempo agora** há um resumo das condições atuais para consulta rápida."
    },
    {
        "gatilhos": ["satelite","satélite","radar"],
        "resposta": "A aba **Satélite e radar** mostra imagens para acompanhar nuvens e precipitação."
    },
    {
        "gatilhos": ["estagio","estágio"],
        "resposta": "A seção **Estágio Curricular** traz orientações, critérios e passos para o estágio."
    },
    {
        "gatilhos": ["projetos","iniciacao","iniciação","extensao","extensão","eventos","vinculados"],
        "resposta": "Em **Projetos** há IC, Extensão, Eventos e Vinculados, com filtros por ano/área e busca."
    },
    {
        "gatilhos": ["contato","email","telefone","endereco","endereço"],
        "resposta": "Use a aba **Contato** para falar com a equipe do LabInstru pelos canais oficiais."
    },
]

def _tenta_faq(q: str):
    qn = _norm(q)
    best, score = None, 0
    for item in KB_ITENS:
        s = sum(1 for g in item["gatilhos"] if g in qn)
        if s > score:
            score, best = s, item
    return best["resposta"] if best and score > 0 else None

# ------------------------------------------------------
# Coleta de fontes (local PDF + web)
# ------------------------------------------------------
ALLOWED_DOMAINS = {
    "inmet.gov.br",
    "cptec.inpe.br",
    "tempo.cptec.inpe.br",
    "satelite.cptec.inpe.br",
    "noaa.gov",
    "wmo.int",
    "metoffice.gov.uk",
    "smn.gob.ar",
    "uea.edu.br",
    "ufam.edu.br",
    "fapeam.am.gov.br",
    "ana.gov.br",
    "gov.br",  # aceita *.gov.br
}

PREFERRED_DOMAINS = [
    "cptec.inpe.br",
    "inmet.gov.br",
]

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

# ---------- Parsers ----------
def _html_to_text(content: bytes) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content or b"", "lxml")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        txt = soup.get_text(separator=" ")
        return _trim(txt, 4000)
    except Exception as e:
        logger.exception("Falha no parse HTML: %s", e)
        txt = re.sub(rb"<[^>]+>", b" ", content or b"", flags=re.S)
        return _trim(txt.decode(errors="ignore"), 4000)

def _pdf_to_text(content: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
        import io
        return _trim(extract_text(io.BytesIO(content or b"")) or "", 4000)
    except Exception as e:
        logger.exception("Falha no parse PDF: %s", e)
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

# ---------- Google CSE ----------
def _cse_keys():
    return (getattr(settings, "CSE_API_KEY", "") or "",
            getattr(settings, "CSE_CX", "") or "")

def _search_web(query: str, limit: int = 3):
    api_key, cx = _cse_keys()
    if not api_key or not cx:
        logger.warning("CSE desabilitado: CSE_API_KEY/CSE_CX ausentes.")
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
            items.append({
                "title": it.get("title",""),
                "url": link,
                "mime": it.get("mime",""),
            })
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        logger.exception("Falha no CSE: %s", e)
        return []

def _search_web_domain(query: str, domain: str, limit: int = 2):
    """Busca restrita a um domínio via CSE (siteSearch)."""
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
            items.append({
                "title": it.get("title",""),
                "url": link,
                "mime": it.get("mime",""),
            })
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        logger.exception("Falha no CSE (domínio %s): %s", domain, e)
        return []

# ---------- Fontes locais (PDF) ----------
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
    """
    Lê fontes locais definidas em settings.ZEUS_LOCAL_SOURCES, ex.:
      ZEUS_LOCAL_SOURCES = [
        {"title":"LabInstru — Resumo","type":"pdf","path": BASE_DIR / "media/LabInstru-resumo.pdf"}
      ]
    """
    out = []
    sources = getattr(settings, "ZEUS_LOCAL_SOURCES", []) or []
    for src in sources:
        stype = (src.get("type") or "").lower()
        path = src.get("path")
        if stype == "pdf" and path:
            txt = _read_pdf_file(str(path))
            if txt:
                out.append({
                    "title": src.get("title") or str(path),
                    "url": f"file://{path}",
                    "snippet": txt[:max_chars_per]
                })
    return out

def _dedup_by_url(items: list[dict]) -> list[dict]:
    seen, res = set(), []
    for it in items:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        res.append(it)
    return res

def _collect_context(question: str, max_web_sources: int = 3):
    """
    Monta contexto com:
      1) Fontes locais (PDFs) — sempre entram
      2) Web preferencial (CPTEC/INMET)
      3) Web geral (restante), até completar max_web_sources
    """
    ctx = []
    local = _local_context(max_chars_per=1200)
    ctx.extend(local)

    # Prioriza CPTEC/INMET (2 por domínio, ajustável)
    for dom in PREFERRED_DOMAINS:
        ctx.extend(_search_web_domain(question, dom, limit=2))

    # Completa com busca geral
    if max_web_sources > 0:
        remaining = max_web_sources
        # já contamos preferenciais como parte do "web"
        web_so_far = len([c for c in ctx if not c["url"].startswith("file://")])
        if web_so_far < max_web_sources:
            remaining = max_web_sources - web_so_far
            ctx.extend(_search_web(question, limit=max(remaining, 0)))

    # Dedup e retorna (locais + web)
    return _dedup_by_url(ctx)

# ------------------------------------------------------
# Prompt/LLM
# ------------------------------------------------------
def _prompt_with_context(q: str, ctx: list[dict]) -> str:
    linhas = [
        "Você é ZEUS, um assistente **humano e simpático** do LabInstru.",
        "Tarefas:",
        "1) Responder **apenas** perguntas de *meteorologia* e/ou *LabInstru*.",
        "2) Use os **trechos de contexto** (locais/web) abaixo quando úteis.",
        "3) Seja **específico** e objetivo; inclua números/datas somente se o trecho trouxer.",
        "4) **Não invente**. Se não souber, diga isso e sugira onde o usuário pode ver no site.",
        "5) Estilo: educado, claro, 2–6 frases, toque humano.",
        "",
        "Pergunta do usuário:",
        _trim(q, 400),
        "",
        "Contexto (pode usar parcial):",
    ]
    for i, c in enumerate(ctx, start=1):
        linhas.append(f"[{i}] {c['title']} — {c['url']}\nTrecho: {c['snippet']}")
    linhas.append("\nSe usar alguma fonte, mencione 'Fontes: [1], [2]…' no final.")
    return "\n".join(linhas)

def _call_gemini(prompt: str) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    model   = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 512}
    }
    if not api_key:
        return "Configuração do serviço de IA indisponível no momento."
    try:
        r = requests.post(url, json=payload, headers={"Content-Type":"application/json"}, timeout=25)
        r.raise_for_status()
        data = r.json()
        txt = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        return txt or "Não consegui gerar resposta agora."
    except Exception as e:
        logger.exception("Falha no Gemini: %s", e)
        return "Tive um erro ao consultar a IA neste momento."

# ------------------------------------------------------
# Endpoint do ZEUS
# ------------------------------------------------------
@require_POST
# @csrf_exempt  # habilite se for chamar de fora sem CSRF
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

    # Escopo
    if not _is_lab_or_meteo(pergunta):
        return JsonResponse({"resposta": _human_refusal(pergunta), "fontes": []})

    # FAQ rápida
    faq = _tenta_faq(pergunta)
    if faq:
        return JsonResponse({"resposta": f"{faq} Posso te guiar até lá se quiser. 🙂", "fontes": []})

    # Contexto: PDF local + web (CPTEC/INMET + geral)
    max_web = getattr(settings, "ZEUS_MAX_WEB_SOURCES", 3)
    context = _collect_context(pergunta, max_web_sources=max_web)

    # Prompt e LLM
    prompt = _prompt_with_context(pergunta, context)
    resposta = _call_gemini(prompt)

    # Fontes (apresentamos mesmo que a IA não cite)
    fontes = [{"titulo": c["title"], "url": c["url"]} for c in context]

    if _norm(resposta).startswith("nao sei") or "não sei" in resposta.lower():
        resposta += "\n\nSe quiser, posso tentar refazer a busca focando em outra palavra-chave. 😉"

    return JsonResponse({"resposta": resposta, "fontes": fontes})
