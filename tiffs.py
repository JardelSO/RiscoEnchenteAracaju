import rasterio
from rasterio.merge import merge
from rasterio.vrt import WarpedVRT  # Usaremos o VRT para a reprojeção
import glob
import os
import shutil

pasta_dos_tifs = r'C:\Users\jarde\Desktop\Grafos\Shape\shp\tiffs'
pasta_corrigida = os.path.join(pasta_dos_tifs, 'tifs_corrigidos')
caminho_saida_mde = os.path.join(pasta_dos_tifs, 'MDE_Aracaju_Completo.tif')
TARGET_CRS = 'EPSG:32724'

if os.path.exists(pasta_corrigida):
    shutil.rmtree(pasta_corrigida)
os.makedirs(pasta_corrigida)

padrao_de_busca = os.path.join(pasta_dos_tifs, 'Bairros_Aracaju-*.tif')
lista_de_arquivos_tif = glob.glob(padrao_de_busca)

if not lista_de_arquivos_tif:
    print("Nenhum arquivo de bairro (.tif) encontrado. Verifique o padrão de busca.")
    exit()

src_files_to_mosaic = []
print("Iniciando correção de CRS e georreferenciamento...")

for fp in lista_de_arquivos_tif:
    try:
        with rasterio.open(fp) as src:
            with WarpedVRT(src, crs=TARGET_CRS, resampling=rasterio.enums.Resampling.nearest) as vrt:
                out_path = os.path.join(pasta_corrigida, os.path.basename(fp))

                out_meta = vrt.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": vrt.height,
                    "width": vrt.width,
                    "transform": vrt.transform,
                    "crs": vrt.crs,
                    "nodata": src.nodata  # Mantém o valor de NoData
                })

                with rasterio.open(out_path, 'w', **out_meta) as dest:
                    dest.write(vrt.read())

                src_files_to_mosaic.append(rasterio.open(out_path))

    except Exception as e:
        print(f"ERRO ao processar {os.path.basename(fp)}: {e}. Pulando.")
        continue

print(f"\nIniciando a criação do mosaico de {len(src_files_to_mosaic)} arquivos CORRIGIDOS...")
try:
    mosaic, out_trans = merge(src_files_to_mosaic)

    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "crs": TARGET_CRS
    })

    with rasterio.open(caminho_saida_mde, "w", **out_meta) as dest:
        dest.write(mosaic)

    print(f"\n Mosaico criado com sucesso em: {caminho_saida_mde}")

except Exception as e:
    print(f"\n ERRO FATAL ao criar o mosaico: {e}")

finally:
    for src in src_files_to_mosaic:
        src.close()

    shutil.rmtree(pasta_corrigida)
    print("\nArquivos temporários de correção removidos.")