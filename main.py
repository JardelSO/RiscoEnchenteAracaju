import geopandas as gpd
import networkx as nx
import rasterio
from rasterio.mask import mask
from shapely.ops import nearest_points
import matplotlib.pyplot as plt
import numpy as np

print("Carregando e alinhando dados geoespaciais...")

mde_path = r'C:\Users\jarde\Desktop\Grafos\Shape\shp\tiffs/MDE_Aracaju_Completo.tif'
mde = rasterio.open(mde_path)
mde_crs = mde.crs

bairros_gdf = gpd.read_file(r'C:\Users\jarde\Desktop\Grafos\Shape\shp\AracajuShp\Aracaju_Bairros_Unificado.shp')

massa_agua_gdf = gpd.read_file(r'C:\Users\jarde\Desktop\Grafos\Shape\shp\AracajuShp\agua/hid_massa_dagua_a.shp')

TARGET_CRS_STRING = 'EPSG:32724'

bairros_gdf = bairros_gdf.to_crs(TARGET_CRS_STRING)
massa_agua_gdf = massa_agua_gdf.to_crs(TARGET_CRS_STRING)

print(f"Reprojetado para CRS (UTM): {TARGET_CRS_STRING}")

G = nx.Graph()
bairros_data = {}

print("Criando nós e calculando adjacências...")
for idx, row in bairros_gdf.iterrows():
    bairro_nome = row['NOME_BAIRR']
    G.add_node(bairro_nome)
    bairros_data[bairro_nome] = {'geometria': row['geometry']}

for i, bairro1 in bairros_gdf.iterrows():
    for j, bairro2 in bairros_gdf.iterrows():
        if i >= j:
            continue
        if bairro1['geometry'].touches(bairro2['geometry']):
            G.add_edge(bairro1['NOME_BAIRR'], bairro2['NOME_BAIRR'])
print(f"Grafo criado com {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")

print("Calculando atributos de risco (Altitude e Proximidade)...")


fontes_agua = massa_agua_gdf.geometry.union_all()

for bairro_nome in G.nodes():
    geom = bairros_data[bairro_nome]['geometria']

    try:
        geom_mde_crs = gpd.GeoSeries([geom], crs=bairros_gdf.crs).to_crs(mde.crs).iloc[0]

        # Extrair pixels
        out_image, out_transform = mask(mde, [geom_mde_crs], crop=True)

        pixels_validos = out_image[out_image > 0]
        if pixels_validos.size > 0:
            altitude_media = pixels_validos.mean()
        else:
            altitude_media = 0

        bairros_data[bairro_nome]['altitude_media'] = altitude_media

    except Exception as e:
        print(f"Aviso: Erro ao processar MDE para {bairro_nome}. Causa: {e}")
        bairros_data[bairro_nome]['altitude_media'] = 0

    p1, p2 = nearest_points(geom, fontes_agua)
    distancia_min_agua = p1.distance(p2)

    bairros_data[bairro_nome]['dist_agua'] = distancia_min_agua

print("Calculando Índice de Risco Composto...")

altitudes = np.array([data['altitude_media'] for data in bairros_data.values()])
distancias = np.array([data['dist_agua'] for data in bairros_data.values()])

def normalize_inverse(arr):
    arr[arr < 1e-6] = 1e-6
    inv_arr = 1 / arr
    return (inv_arr - np.min(inv_arr)) / (np.max(inv_arr) - np.min(inv_arr))

risco_alt_norm = normalize_inverse(altitudes)
risco_dist_norm = normalize_inverse(distancias)

alpha_altitude = 0.30
beta_proximidade = 0.70

riscos = {}
bairro_nomes = list(G.nodes())
for i, bairro_nome in enumerate(bairro_nomes):
    risco_composto = (alpha_altitude * risco_alt_norm[i]) + (beta_proximidade * risco_dist_norm[i])
    riscos[bairro_nome] = risco_composto

max_risco = max(riscos.values())
min_risco = min(riscos.values())

risco_col = []
for bairro in bairros_gdf['NOME_BAIRR']:
    risco_norm = (riscos[bairro] - min_risco) / (max_risco - min_risco)
    G.nodes[bairro]['risco_final'] = risco_norm
    risco_col.append(risco_norm)

bairros_gdf['RISCO'] = risco_col

print("--- Risco Final (0=Baixo, 1=Alto) ---")
for bairro in sorted(riscos, key=riscos.get, reverse=True):
    print(f"{bairro}: {G.nodes[bairro]['risco_final']:.4f}")

print("Gerando mapa de risco...")
fig, ax = plt.subplots(1, 1, figsize=(10, 10))

ax.set_axis_off()


bairros_gdf.plot(column='RISCO', ax=ax, legend=True, cmap='Reds',
                 legend_kwds={'label': "Índice de Risco de Enchente"})
massa_agua_gdf.plot(ax=ax, color='blue', alpha=0.5)

ax.set_title("Risco de Enchente por Bairro - Aracaju (Baseado em Altitude e Proximidade)")




plt.show()

mde.close()