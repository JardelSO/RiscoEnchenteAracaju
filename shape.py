import geopandas as gpd
import glob
import os

pasta_dos_bairros = r'C:\Users\jarde\Desktop\Grafos\Shape\shp\shp_unificados'


padrao_de_busca = os.path.join(pasta_dos_bairros, '*.shp')
lista_de_arquivos_shp = glob.glob(padrao_de_busca)

lista_gdfs = []

print(f"Encontrados {len(lista_de_arquivos_shp)} shapefiles de bairros...")

for shp_file in lista_de_arquivos_shp:
    try:
        gdf_bairro = gpd.read_file(shp_file)
        if 'NOME_BAIRRO' not in gdf_bairro.columns:
            nome_bairro = os.path.basename(shp_file).replace('.shp', '')
            gdf_bairro['NOME_BAIRR'] = nome_bairro
            print(f"Lendo e atribuindo nome: {nome_bairro}")

        lista_gdfs.append(gdf_bairro)
    except Exception as e:
        print(f"Erro ao ler {shp_file}: {e}")

if lista_gdfs:
    bairros_gdf = gpd.pd.concat(lista_gdfs, ignore_index=True)

    print("\n--- Concatenação Concluída ---")
    print("GeoDataFrame unificado:")
    print(bairros_gdf.head())


    caminho_saida = os.path.join(pasta_dos_bairros, 'Aracaju_Bairros_Unificado.shp')
    bairros_gdf.to_file(caminho_saida)
    num_total_bairros = bairros_gdf.shape[0]
    print(f" Número TOTAL de bairros carregados: {num_total_bairros}")
    print(f"\nArquivo unificado salvo em: {caminho_saida}")

else:
    print("Nenhum arquivo .shp encontrado no diretório. Verifique o caminho.")