import geopandas as gpd
from shapely.validation import make_valid

# 1) Ler o shapefile
gdf = gpd.read_file("Mun_Manaus.shp")

# 2) Reprojetar para WGS84 (lon/lat) — GeoJSON padrão
gdf = gdf.to_crs(4326)

# 3) Unir tudo em uma única geometria (dissolver geral)
geom = gdf.geometry.unary_union  # MultiPolygon/Polygon

# 4) Garantir geometria válida (Shapely 2.x)
try:
    geom = make_valid(geom)
except Exception:
    # fallback p/ versões antigas: "conserta" com buffer(0)
    geom = geom.buffer(0)

# 5) (Opcional) Simplificar para reduzir tamanho do arquivo
# geom = geom.simplify(0.0005, preserve_topology=True)

# 6) Salvar o CONTORNO como POLÍGONO
gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326") \
  .to_file("contorno_poligono.geojson", driver="GeoJSON")

# 7) Salvar o CONTORNO como LINHA (apenas a borda)
linha = geom.boundary
gpd.GeoDataFrame(geometry=[linha], crs="EPSG:4326") \
  .to_file("contorno_linha.geojson", driver="GeoJSON")

print("Pronto! Gerados: contorno_poligono.geojson e contorno_linha.geojson")
