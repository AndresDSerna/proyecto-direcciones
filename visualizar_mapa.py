import boto3
import pandas as pd
import folium
import io

# --- CONFIGURACIÓN ---
# El nombre de tu bucket de salida donde está el Excel
BUCKET_DE_SALIDA = "resultados-direcciones-wenia-2025"
# El nombre del archivo Excel
NOMBRE_DEL_EXCEL = "resultados_acumulados.xlsx"
# Nombre que tendrá el archivo del mapa
NOMBRE_DEL_MAPA = "mapa_final.html"

def crear_mapa_desde_s3(bucket: str, key_excel: str):
    """
    Descarga el archivo Excel desde S3, lee las coordenadas y genera un mapa.
    """
    try:
        # 1. Conectarse a S3 y descargar el archivo Excel en memoria
        s3 = boto3.client('s3')
        print(f"📥 Descargando '{key_excel}' desde el bucket '{bucket}'...")
        response = s3.get_object(Bucket=bucket, Key=key_excel)
        
        # 2. Leer el Excel con pandas
        excel_data = response['Body'].read()
        df = pd.read_excel(io.BytesIO(excel_data))
        
        # Eliminar filas donde no se encontraron coordenadas
        df.dropna(subset=['latitud', 'longitud'], inplace=True)
        print(f"✅ Archivo leído. Se graficarán {len(df)} puntos.")

    except Exception as e:
        print(f"❌ Error al leer el archivo desde S3: {e}")
        return

    # 3. Crear y centrar el mapa
    mapa = folium.Map(location=[4.60971, -74.08175], zoom_start=6)

    # 4. Añadir un marcador por cada dirección en el Excel
    for _, fila in df.iterrows():
        folium.Marker(
            location=[fila["latitud"], fila["longitud"]],
            popup=f"<b>{fila['variante_similar']}</b><br>Original: {fila['original']}<br>Score: {fila['similitud']}%",
            tooltip="Clic para más info"
        ).add_to(mapa)

    # 5. Guardar el mapa en un archivo HTML
    mapa.save(NOMBRE_DEL_MAPA)
    print(f"\n🗺️  ¡Mapa generado! Abre el archivo '{NOMBRE_DEL_MAPA}' en tu navegador.")

# --- EJECUCIÓN DEL SCRIPT ---
if __name__ == "__main__":
    # Reemplaza con el nombre de tu bucket si es diferente
    crear_mapa_desde_s3(BUCKET_DE_SALIDA, NOMBRE_DEL_EXCEL)