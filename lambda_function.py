import boto3
import pandas as pd
import re
from thefuzz import fuzz
import io
import os
import requests
import urllib.parse
import time

# --- Clientes de AWS ---
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')
textract_client = boto3.client('textract')

# --- CONFIGURACIÓN ---
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
OUTPUT_FILE_KEY = os.environ.get('OUTPUT_FILE_KEY')

# --- FUNCIONES AUXILIARES ---

def get_google_api_key():
    """Obtiene la clave de API de Google de forma segura desde Parameter Store."""
    try:
        parameter = ssm_client.get_parameter(Name='/wenia/google_api_key', WithDecryption=True)
        return parameter['Parameter']['Value']
    except Exception as e:
        print(f"Error al obtener la clave de API: {e}")
        raise e

GRUPOS_NOMENCLATURRAS = {
    'CARRERA': ['Carrera', 'Cra', 'Kra', 'Cr', 'K'], 'CALLE': ['Calle', 'Cl', 'Cll'],
    'AVENIDA': ['Avenida', 'Av', 'Ak'], 'DIAGONAL': ['Diagonal', 'Dg'],
    'TRANSVERSAL': ['Transversal', 'Tv', 'Tr']
}

def encontrar_grupo_correcto(nomenclatura: str):
    nomenclatura_lower = nomenclatura.lower()
    for _, variantes in GRUPOS_NOMENCLATURRAS.items():
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
            return location["lat"], location["lng"]
    except requests.exceptions.RequestException as e:
        print(f"Error API: {e}")
    return None, None

def extraer_todas_las_direcciones(texto: str):
    """Busca y devuelve TODAS las direcciones en un texto."""
    patron = r'\b(?:' + '|'.join(sum(GRUPOS_NOMENCLATURRAS.values(), [])) + r')[\s\.]+?.*?#.*?-.*?\d+'
    return re.findall(patron, texto, re.IGNORECASE)

# --- FUNCIÓN PRINCIPAL DE LAMBDA ---
def lambda_handler(event, context):
    API_KEY_GOOGLE = get_google_api_key()

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    print(f"Nuevo archivo detectado: s3://{bucket}/{key}")

    contenido_archivo = ""
    if key.lower().endswith('.pdf'):
        print("Archivo PDF detectado. Usando AWS Textract...")
        response = textract_client.start_document_text_detection(
            DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}}
        )
        job_id = response['JobId']
        
        job_status = 'IN_PROGRESS'
        while job_status == 'IN_PROGRESS':
            time.sleep(5)
            job_result = textract_client.get_document_text_detection(JobId=job_id)
            job_status = job_result['JobStatus']
        
        if job_status == 'SUCCEEDED':
            for item in job_result.get('Blocks', []):
                if item['BlockType'] == 'LINE':
                    contenido_archivo += item['Text'] + '\n'
            print("Texto extraído de PDF.")
        else:
            print(f"El trabajo de Textract falló: {job_status}")
            return {'statusCode': 500, 'body': 'Fallo en Textract.'}
    else:
        print("Archivo de texto plano detectado. Leyendo desde S3...")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        contenido_archivo = response['Body'].read().decode('utf-8')
    
    lista_direcciones_base = extraer_todas_las_direcciones(contenido_archivo)
    if not lista_direcciones_base:
        print("No se encontraron direcciones en el archivo.")
        return {'statusCode': 400, 'body': 'No se encontraron direcciones.'}
    print(f"Se encontraron {len(lista_direcciones_base)} direcciones para procesar: {lista_direcciones_base}")

    todos_los_resultados = []
    for direccion in lista_direcciones_base:
        print(f"Procesando variantes para: '{direccion}'")
        nuevos_resultados = generar_y_priorizar(direccion)
        if nuevos_resultados:
            for res in nuevos_resultados:
                lat, lng = obtener_coordenadas(res['variante_similar'], API_KEY_GOOGLE)
                res['latitud'] = lat
                res['longitud'] = lng
            todos_los_resultados.extend(nuevos_resultados)
        
    if not todos_los_resultados:
        print("No se generaron coincidencias válidas para ninguna dirección.")
        return {'statusCode': 200, 'body': 'No se generaron coincidencias.'}

    df_nuevos = pd.DataFrame(todos_los_resultados)

    try:
        response = s3_client.get_object(Bucket=OUTPUT_BUCKET, Key=OUTPUT_FILE_KEY)
        excel_data = response['Body'].read()
        df_existente = pd.read_excel(io.BytesIO(excel_data))
        df_final = pd.concat([df_existente, df_nuevos], ignore_index=True)
        print(f"Archivo existente leído. Se añadirán {len(df_nuevos)} nuevos registros.")
    except s3_client.exceptions.NoSuchKey:
        print(f"No se encontró el archivo Excel. Se creará uno nuevo.")
        df_final = df_nuevos

    with io.BytesIO() as output:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        s3_client.put_object(Bucket=OUTPUT_BUCKET, Key=OUTPUT_FILE_KEY, Body=output.getvalue())
    
    print(f"¡Éxito! El archivo 's3://{OUTPUT_BUCKET}/{OUTPUT_FILE_KEY}' ha sido actualizado.")
    return {'statusCode': 200, 'body': 'Proceso completado.'}