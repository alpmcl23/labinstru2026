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

# siteapp/views.py
import os, json
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from django.conf import settings
from django.shortcuts import render

import folium
from folium import DivIcon, TileLayer
from folium.plugins import Fullscreen
from folium.features import Tooltip
from branca.element import Template, MacroElement






# =========================
# CONFIG / CONSTANTES
# =========================

# (use variável de ambiente em produção)
PURPLEAIR_API_KEY = "D949FBD6-5C4D-11F0-81BE-42010A80001F"

# Limites da RM de Manaus (para travar o pan)
MANAUS_BOUNDS = {"nwlat": -2.60, "nwlng": -60.70, "selat": -3.80, "selng": -59.10}

# Visão inicial
VIEW_CENTER = (-3.07, -60.02)
VIEW_ZOOM   = 12

# Altura fixa (combine com --map-h no template)
MAP_H = 1100  # px

# Estilo dos círculos
CIRCLE_SIZE_PX = 38
FONT_SIZE_PX   = 12
FONT_SIZE_UNIT = 10

# Caminho do contorno (GeoJSON)
CONTORNO_PATH = os.path.join(settings.BASE_DIR, "static", "geo", "contorno_manaus.geojson")
# fallback (dev)
if not os.path.exists(CONTORNO_PATH):
    alt = "/mnt/data/contorno_manaus.geojson"
    if os.path.exists(alt):
        CONTORNO_PATH = alt

# =========================
# OVERLAYS / CONTROLES
# =========================

class SelvaLogoOnly(MacroElement):
    _template = Template("""
    {% macro html(this, kwargs) %}
    <div style="position:absolute; top:12px; right:12px; z-index:9999; pointer-events:none;">
      <img src="{{ this.url }}" alt="SELVA" style="height:140px; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35));">
    </div>
    {% endmacro %}
    """)
    def __init__(self, url: str):
        super().__init__()
        self.url = url

class MaxBounds(MacroElement):
    """Trava o pan dentro do retângulo (sem mexer no zoom)."""
    _template = Template("""
    {% macro script(this, kwargs) %}
    (function(){
      var m = {{ this._parent.get_name() }};
      var b = L.latLngBounds(
        [{{ this.south }}, {{ this.west }}],
        [{{ this.north }}, {{ this.east }}]
      );
      m.setMaxBounds(b);
      m.options.maxBoundsViscosity = 1.0;
    })();
    {% endmacro %}
    """)
    def __init__(self, south, west, north, east):
        super().__init__()
        self.south, self.west, self.north, self.east = south, west, north, east

# =========================
# HELPERS
# =========================

def _ts_manaus(ts):
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(timezone(timedelta(hours=-4)))
    except Exception:
        return None

def _cor_pm25(v):
    v = float(v)
    if v <= 25:   return "#39e639"
    if v <= 50:   return "#ffff00"
    if v <= 75:   return "#f4a460"   # areia p/ “Ruim”, como na sua arte
    if v <= 125:  return "#ff3333"
    if v <= 160:  return "#a633cc"
    return "#7e0023"

def _f_to_c(f): return (f - 32.0) * 5.0 / 9.0
def _temp_simple_c_minus8f(t_raw_f): return _f_to_c(t_raw_f - 8.0)

def _pick_raw_f(s):
    for k in ("temperature", "temperature_a", "temperature_b"):
        v = s.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return None

def _cor_temp_c(t_c):
    if t_c <= 0:  return "#4575b4"
    if t_c <= 10: return "#74add1"
    if t_c <= 20: return "#abd9e9"
    if t_c <= 25: return "#fee090"
    if t_c <= 30: return "#fdae61"
    if t_c <= 35: return "#f46d43"
    return "#a50026"

def _circle_badge_html(texto, bg, dx=0, dy=0, with_degree=False):
    size = CIRCLE_SIZE_PX
    fs   = FONT_SIZE_PX
    fsu  = FONT_SIZE_UNIT
    if with_degree:
        inner = f"{texto:.1f}<span style='font-size:{fsu}px; font-weight:700;'>°</span>"
    else:
        inner = f"{texto:.1f}"
    return (
        f"<div style=\"transform:translate({dx}px,{dy}px);"
        f"width:{size}px;height:{size}px;line-height:{size}px;border-radius:50%;"
        f"background:{bg}; color:#111; border:2px solid #222; "
        f"font-weight:800; font-size:{fs}px; text-align:center; "
        f"font-family:system-ui,-apple-system,Segoe UI,Roboto; "
        f"box-shadow:0 1px 2px rgba(0,0,0,.35);\">{inner}</div>"
    )

# desloca pinos em mesma célula
NUDGE_RING = [(0,0),(18,0),(-18,0),(0,18),(0,-18),(14,14),(-14,14),(14,-14),(-14,-14),(26,10),(-26,10),(26,-10),(-26,-10)]
def _nudge_for(lat, lon, cell_counts, precision=3):
    key = (round(lat, precision), round(lon, precision))
    idx = cell_counts[key]
    cell_counts[key] += 1
    dx, dy = NUDGE_RING[idx % len(NUDGE_RING)]
    return dx, dy

def _add_contorno_sem_checkbox(mapa):
    """Adiciona o contorno de Manaus SEM controle de camada (sempre visível)."""
    if not os.path.exists(CONTORNO_PATH):
        return
    try:
        with open(CONTORNO_PATH, "r", encoding="utf-8") as f:
            manaus_geo = json.load(f)
        folium.GeoJson(
            manaus_geo,
            style_function=lambda _:{
                "fillColor": "#0000",   # sem preenchimento
                "color": "#145DA0",     # azul do contorno
                "weight": 3,
                "fillOpacity": 0.0,
                # "dashArray": "6,4",   # <- descomente se quiser tracejado
            },
            highlight_function=lambda _:{
                "color": "#0b4a91",
                "weight": 4
            },
            tooltip=Tooltip("Município de Manaus")
        ).add_to(mapa)   # direto no mapa (sem FeatureGroup/LayerControl)
    except Exception:
        pass

# =========================
# VIEW
# =========================

def condicoes_atmosfera(request):
    logo_url = "/static/img/selva.png"

    # ----- MAPA 1 — Temperatura -----
    mapa_temp = folium.Map(
        location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM, tiles=None,
        control_scale=True, width="100%", height=f"{MAP_H}px",
        prefer_canvas=True, zoom_control=True, dragging=True,
        scrollWheelZoom=True, doubleClickZoom=True, touchZoom=True
    )
    TileLayer('OpenStreetMap', control=False).add_to(mapa_temp)
    mapa_temp.add_child(SelvaLogoOnly(logo_url))
    mapa_temp.add_child(MaxBounds(
        MANAUS_BOUNDS["selat"], MANAUS_BOUNDS["nwlng"],
        MANAUS_BOUNDS["nwlat"], MANAUS_BOUNDS["selng"]
    ))
    Fullscreen(position="topleft", force_separate_button=True).add_to(mapa_temp)

    # CONTORNO sempre visível
    _add_contorno_sem_checkbox(mapa_temp)

    cells_temp = defaultdict(int)
    try:
        r = requests.get(
            "https://api.purpleair.com/v1/sensors",
            params={
                "fields": "latitude,longitude,name,temperature,temperature_a,temperature_b,last_seen",
                "location_type": 0, "max_age": 180, "limit": 1000,
                "nwlng": MANAUS_BOUNDS["nwlng"], "nwlat": MANAUS_BOUNDS["nwlat"],
                "selng": MANAUS_BOUNDS["selng"], "selat": MANAUS_BOUNDS["selat"],
            },
            headers={"X-API-Key": PURPLEAIR_API_KEY}, timeout=20
        )
        if r.ok:
            js = r.json(); fields = js.get("fields", [])
            for row in js.get("data", []):
                s = dict(zip(fields, row))
                lat, lon = s.get("latitude"), s.get("longitude")
                if lat is None or lon is None:
                    continue
                t_raw_f = _pick_raw_f(s)
                if t_raw_f is None:
                    continue
                t_c = _temp_simple_c_minus8f(t_raw_f)
                cor = _cor_temp_c(t_c)
                hora = _ts_manaus(s.get("last_seen"))
                dx, dy = _nudge_for(lat, lon, cells_temp)
                popup = f"<b>{s.get('name') or 'Sensor'}</b>"
                if hora: popup += f"<br>Atualizado: {hora:%d/%m/%Y %H:%M:%S}"
                folium.Marker(
                    [lat, lon],
                    tooltip=s.get("name") or "Sensor",
                    popup=popup,
                    icon=DivIcon(
                        icon_size=(CIRCLE_SIZE_PX, CIRCLE_SIZE_PX),
                        icon_anchor=(CIRCLE_SIZE_PX//2, CIRCLE_SIZE_PX//2),
                        html=_circle_badge_html(t_c, cor, dx, dy, with_degree=True),
                    ),
                ).add_to(mapa_temp)
    except Exception:
        pass

    # ----- MAPA 2 — PM2.5 -----
    mapa_ar = folium.Map(
        location=list(VIEW_CENTER), zoom_start=VIEW_ZOOM, tiles=None,
        control_scale=True, width="100%", height=f"{MAP_H}px",
        prefer_canvas=True, zoom_control=True, dragging=True,
        scrollWheelZoom=True, doubleClickZoom=True, touchZoom=True
    )
    TileLayer('OpenStreetMap', control=False).add_to(mapa_ar)
    mapa_ar.add_child(SelvaLogoOnly(logo_url))
    mapa_ar.add_child(MaxBounds(
        MANAUS_BOUNDS["selat"], MANAUS_BOUNDS["nwlng"],
        MANAUS_BOUNDS["nwlat"], MANAUS_BOUNDS["selng"]
    ))
    Fullscreen(position="topleft", force_separate_button=True).add_to(mapa_ar)

    # CONTORNO sempre visível
    _add_contorno_sem_checkbox(mapa_ar)

    cells_pm = defaultdict(int)
    try:
        rr = requests.get(
            "https://api.purpleair.com/v1/sensors",
            params={
                "fields": "latitude,longitude,name,pm2.5_10minute,pm2.5,pm2.5_atm,pm2.5_cf_1,last_seen",
                "location_type": 0, "max_age": 180, "limit": 1000,
                "nwlng": MANAUS_BOUNDS["nwlng"], "nwlat": MANAUS_BOUNDS["nwlat"],
                "selng": MANAUS_BOUNDS["selng"], "selat": MANAUS_BOUNDS["selat"],
            },
            headers={"X-API-Key": PURPLEAIR_API_KEY}, timeout=20
        )
        if rr.ok:
            js = rr.json(); fields = js.get("fields", [])
            for row in js.get("data", []):
                s = dict(zip(fields, row))
                lat, lon = s.get("latitude"), s.get("longitude")
                if lat is None or lon is None:
                    continue
                pm = (s.get("pm2.5_10minute") if s.get("pm2.5_10minute") is not None else
                      s.get("pm2.5") if s.get("pm2.5") is not None else
                      s.get("pm2.5_atm") if s.get("pm2.5_atm") is not None else
                      s.get("pm2.5_cf_1"))
                if pm is None:
                    continue
                pm = float(pm)
                hora = _ts_manaus(s.get("last_seen"))
                dx, dy = _nudge_for(lat, lon, cells_pm)
                popup = f"<b>{s.get('name') or 'Sensor'}</b><br>PM2.5: <b>{pm:.1f}</b> µg/m³"
                if hora: popup += f"<br>Atualizado: {hora:%d/%m/%Y %H:%M:%S}"
                folium.Marker(
                    [lat, lon],
                    tooltip=s.get("name") or "Sensor",
                    popup=popup,
                    icon=DivIcon(
                        icon_size=(CIRCLE_SIZE_PX, CIRCLE_SIZE_PX),
                        icon_anchor=(CIRCLE_SIZE_PX//2, CIRCLE_SIZE_PX//2),
                        html=_circle_badge_html(pm, _cor_pm25(pm), dx, dy, with_degree=False),
                    ),
                ).add_to(mapa_ar)
    except Exception:
        pass

    ctx = {
        "mapa_temp_html": mapa_temp._repr_html_(),
        "mapa_ar_html":   mapa_ar._repr_html_(),
        "proxima": (datetime.now() + timedelta(minutes=10)).strftime("%H:%M"),
    }
    return render(request, "siteapp/condicoes.html", ctx)



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




# siteapp/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
import requests, json, re, unicodedata, html
from urllib.parse import urlparse

# ==== Dependências sugeridas (instale no seu venv) ====
# pip install requests beautifulsoup4 lxml pdfminer.six python-dotenv

# ------------------------------------------------------
# Utilidades
# ------------------------------------------------------
def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = re.sub(r"[\u0300-\u036f]", "", s)
    return s

def _is_lab_or_meteo(q: str) -> bool:
    """Permite LabInstru e Meteorologia em geral (Amazônia/Manaus etc.)."""
    qn = _norm(q)
    termos = [
        # LabInstru / site
        "labinstru","site","pagina","página","aba","uea","quem somos","estacao","estação",
        "rede hobo","tempo agora","satelite","satélite","radar","estagio","estágio",
        "projetos","iniciacao","iniciação","extensao","extensão","eventos","contato",
        # Meteorologia geral
        "meteorologia","chuva","precipitacao","precipitação","temperatura","umidade","vento",
        "frente fria","ensaio","conveccao","convecção","zcas","zcit","el nino","el niño","la nina",
        "enso","seca","enchente","manaus","amazonia","índice de calor","indice de calor",
        "disdrometro","disdrômetro","noaa","cptec","inmet","onamet","wmo"
    ]
    return any(t in qn for t in termos)

def _human_refusal(q: str) -> str:
    return (
        "Desculpa, eu só consigo ajudar com **assuntos do LabInstru e de meteorologia**. "
        "Se quiser, posso responder algo como: *Quais abas existem no site?*, "
        "*Onde vejo os dados da estação?*, ou *Explique El Niño em Manaus* 🙂"
    )

def _trim(txt: str, limit: int = 2000) -> str:
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]

# ------------------------------------------------------
# Mini-FAQ (LabInstru) para respostas rápidas sem chamar LLM
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
# Coleta de fontes (web e PDF)
# ------------------------------------------------------
ALLOWED_DOMAINS = {
    # institucionais/meteo confiáveis
    "inmet.gov.br","cptec.inpe.br","climatempo.com.br","noaa.gov","wmo.int",
    "metoffice.gov.uk","smn.gob.ar","cptec","inpe.br","governo","gov.br",
    "uea.edu.br","ufam.edu.br","fapeam.am.gov.br","ana.gov.br","anac.gov.br",
    "tempo.cptec.inpe.br","satelite.cptec.inpe.br",
}

def _domain_allowed(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower()
        return any(d in netloc for d in ALLOWED_DOMAINS)
    except Exception:
        return False

def _search_web(query: str, limit: int = 3):
    """
    Usa Google Programmable Search (CSE). Configure em settings:
      CSE_API_KEY, CSE_CX
    """
    api_key = getattr(settings, "CSE_API_KEY", "")
    cx      = getattr(settings, "CSE_CX", "")
    if not api_key or not cx:
        return []  # sem chave, sem busca

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": limit}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in data.get("items", []):
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
    except Exception:
        return []

# HTML → texto
def _html_to_text(content: bytes) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "lxml")
        # remove scripts/styles
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        txt = soup.get_text(separator=" ")
        return _trim(txt, 4000)
    except Exception:
        # fallback simples
        txt = re.sub(rb"<[^>]+>", b" ", content or b"", flags=re.S)
        return _trim(txt.decode(errors="ignore"), 4000)

# PDF → texto
def _pdf_to_text(content: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
        import io
        return _trim(extract_text(io.BytesIO(content)) or "", 4000)
    except Exception:
        return ""

def _fetch_text(url: str) -> str:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        ctype = r.headers.get("Content-Type","").lower()
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            return _pdf_to_text(r.content)
        return _html_to_text(r.content)
    except Exception:
        return ""

def _collect_context(question: str, max_sources: int = 3):
    """Busca na web e retorna [(titulo,url,trecho_texto), ...]"""
    results = _search_web(question, limit=max_sources)
    out = []
    for res in results:
        txt = _fetch_text(res["url"])
        if not txt:
            continue
        out.append({
            "title": res["title"] or res["url"],
            "url": res["url"],
            "snippet": txt[:1200]  # trechinho
        })
    return out

# ------------------------------------------------------
# Chamada ao Gemini com contexto + regras
# ------------------------------------------------------
def _prompt_with_context(q: str, ctx: list[dict]) -> str:
    linhas = [
        "Você é ZEUS, um assistente **humano e simpático** do LabInstru.",
        "Tarefas:",
        "1) Responder **apenas** perguntas de *meteorologia* e/ou *LabInstru*.",
        "2) Use os **trechos de contexto** (web/PDF) abaixo quando úteis.",
        "3) Seja **específico** e objetivo; inclua números/datas somente se o trecho trouxer.",
        "4) **Não invente**. Se não souber, diga isso e sugira onde o usuário pode ver no site.",
        "5) Estilo: educado, claro, 2–6 frases, toque humano.",
        "",
        "Pergunta do usuário:",
        q,
        "",
        "Contexto (pode usar parcial):",
    ]
    for i, c in enumerate(ctx, start=1):
        linhas.append(f"[{i}] {c['title']} — {c['url']}\nTrecho: {c['snippet']}")
    linhas.append("\nSe usar alguma fonte, mencione 'Fontes: [1], [2]…' no final.")
    return "\n".join(linhas)

def _call_gemini(prompt: str) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    model   = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 512}
    }
    if not api_key:
        return "Configuração do serviço indisponível no momento."
    try:
        r = requests.post(url, json=payload, timeout=25)
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
    except Exception:
        return "Tive um erro ao consultar a IA neste momento."

# ------------------------------------------------------
# Endpoint do ZEUS
# ------------------------------------------------------
@require_POST
def api_zeus(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        pergunta = (body.get("pergunta") or "").strip()
    except Exception:
        return JsonResponse({"resposta": "Não entendi sua pergunta."}, status=400)

    if not pergunta:
        return JsonResponse({"resposta": "Digite sua pergunta 🙂"})

    # Escopo permitido
    if not _is_lab_or_meteo(pergunta):
        return JsonResponse({
            "resposta": _human_refusal(pergunta),
            "fontes": []
        })

    # FAQ rápida (LabInstru)
    faq = _tenta_faq(pergunta)
    if faq:
        # Tom humano curto
        return JsonResponse({"resposta": f"{faq} Posso te guiar até lá se quiser. 🙂", "fontes": []})

    # Busca web/PDF (contexto)
    context = _collect_context(pergunta, max_sources=3)

    # Prompt e LLM
    prompt = _prompt_with_context(pergunta, context)
    resposta = _call_gemini(prompt)

    # Fontes (apresentamos mesmo que a IA não cite)
    fontes = [{"titulo": c["title"], "url": c["url"]} for c in context]

    # Se por acaso a LLM disser que não sabe, mantenha humano
    if _norm(resposta).startswith("nao sei") or "não sei" in resposta.lower():
        resposta += "\n\nSe quiser, posso tentar refazer a busca focando em outra palavra-chave. 😉"

    return JsonResponse({"resposta": resposta, "fontes": fontes})

