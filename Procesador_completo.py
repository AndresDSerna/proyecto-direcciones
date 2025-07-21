import json
import re
import time
import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError
from thefuzz import fuzz

# CONFIGURACIÓN ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    API_KEY = config['google_api_key']
    BUCKET = config['s3_bucket_output']
    KEY_ORIGINAL = config['s3_key_original']
    EXCEL_OUTPUT = config['excel_output_file']
except FileNotFoundError:
    print("❌ Error: No se encontró el archivo 'config.json'. Por favor, créalo siguiendo las instrucciones del README.")
    exit()

# --- FUNCIONES AUXILIARES ---
GRUPOS_NOMENCLATURAS = {
    'CARRERA': ['Carrera', 'Cra', 'Kra', 'Cr', 'K'], 'CALLE': ['Calle', 'Cl', 'Cll'],
    'AVENIDA': ['Avenida', 'Av', 'Ak'], 'DIAGONAL': ['Diagonal', 'Dg'],
    'TRANSVERSAL': ['Transversal', 'Tv', 'Tr']
}

def encontrar_grupo_correcto(nomenclatura: str):
    nomenclatura_lower = nomenclatura.lower()
    for _, variantes in GRUPOS_NOMENCLATURAS.items():
        if nomenclatura_lower in [v.lower() for v in variantes]:
            return variantes
    return None

def generar_y_priorizar(direccion_original: str):
    
    partes = re.match(r'(\w+)\s*(\d+\w*)\s*[#|N]\w*\s*(\d+\w*)\s*-\s*(\d+)', direccion_original, re.IGNORECASE)
    if not partes: return []
    nomenclatura_original, via_principal, via_secundaria, num_final = partes.groups()
    grupo_correcto = encontrar_grupo_correcto(nomenclatura_original)
    if not grupo_correcto: return []
    separadores = ['#', 'Nro', 'Numero', 'Num']
    direcciones_generadas = [f"{nom} {via_principal} {sep} {via_secundaria} - {num_final}" for nom in grupo_correcto for sep in separadores]
    resultados_sobre_90 = []
    for variante in direcciones_generadas:
        score = fuzz.ratio(direccion_original.lower(), variante.lower())
        if score > 90:
            resultados_sobre_90.append({"original": direccion_original, "variante_similar": variante, "similitud": score})
    if not resultados_sobre_90: return []
    resultados_100 = [r for r in resultados_sobre_90 if r['similitud'] == 100]
    return resultados_100 if resultados_100 else resultados_sobre_90

def obtener_coordenadas(direccion: str, api_key: str):
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{direccion}, Colombia", "key": api_key}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            print(f"  -> Coordenadas para '{direccion}': ({location['lat']}, {location['lng']})")
            return location["lat"], location["lng"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Error API: {e}")
    return None, None

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    # 1. LEER DIRECCIONES DESDE S3
    lista_de_direcciones_base = []
    try:
        s3 = boto3.client('s3')
        print(f"📥 Conectando a S3 para leer 's3://{BUCKET}/{KEY_ORIGINAL}'...")
        response = s3.get_object(Bucket=BUCKET, Key=KEY_ORIGINAL)
        contenido_archivo = response['Body'].read().decode('utf-8')
        lista_de_direcciones_base = [line for line in contenido_archivo.splitlines() if line.strip()]
        print(f"✅ Archivo leído. Se encontraron {len(lista_de_direcciones_base)} direcciones.")
    except ClientError as e:
        print(f"❌ Error de AWS al leer el archivo: {e}")

    # 2. PROCESAR Y GEOLOCALIZAR
    if lista_de_direcciones_base:
        todos_los_resultados = []
        for direccion in lista_de_direcciones_base:
            resultados_similares = generar_y_priorizar(direccion)
            for res in resultados_similares:
                lat, lng = obtener_coordenadas(res['variante_similar'], API_KEY)
                res['latitud'] = lat
                res['longitud'] = lng
                todos_los_resultados.append(res)
                time.sleep(0.1)

        # 3. GUARDAR RESULTADOS EN EXCEL
        if todos_los_resultados:
            df = pd.DataFrame(todos_los_resultados)
            df.to_excel(EXCEL_OUTPUT, index=False)
            print(f"\n✨ ¡Proceso completado! Se guardaron {len(todos_los_resultados)} resultados en '{EXCEL_OUTPUT}'.")
            print(df)
        else:
            print("\nNo se encontraron resultados válidos.")