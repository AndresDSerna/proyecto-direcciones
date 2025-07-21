import pandas as pd
import folium
import json


try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    EXCEL_INPUT = config['excel_output_file']
    MAP_OUTPUT = config['map_output_file']
except FileNotFoundError:
    print("❌ Error: No se encontró 'config.json'. Ejecuta primero 'procesador_completo.py'.")
    exit()


df = pd.read_excel(EXCEL_INPUT)
df.dropna(subset=['latitud', 'longitud'], inplace=True)

mapa = folium.Map(location=[4.60971, -74.08175], zoom_start=6)

for index, fila in df.iterrows():
    folium.Marker(
        location=[fila["latitud"], fila["longitud"]],
        popup=f"<b>{fila['variante_similar']}</b><br>Score: {fila['similitud']}%",
    ).add_to(mapa)

mapa.save(MAP_OUTPUT)
print(f"🗺️ ¡Mapa generado! Abre el archivo '{MAP_OUTPUT}' en tu navegador.")