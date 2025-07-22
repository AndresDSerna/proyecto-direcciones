# 🗺️ Proyecto de Procesamiento Automático de Direcciones (Versión 2)

Este proyecto implementa una arquitectura **serverless en AWS** para procesar archivos `.txt` o `.pdf` que contienen direcciones colombianas. Extrae texto, busca variantes lógicas de las direcciones, las geocodifica con Google Maps y guarda los resultados de forma acumulativa en un archivo Excel. Finalmente, permite visualizar las ubicaciones en un mapa interactivo.

---

## ⚙️ Arquitectura del Sistema

El flujo general funciona así:

1. 📤 Un archivo `.txt` o `.pdf` es subido a un **bucket S3 de entrada**.
2. 🚀 Este evento activa una **Función Lambda**.
3. 📄 Si el archivo es PDF, se extrae el texto usando **AWS Textract**.
4. 🧠 Se identifican direcciones, se generan variantes y se filtran por similitud.
5. 🔐 Se obtiene una clave API desde **AWS Parameter Store**.
6. 🗺️ Se consulta la **API de Google Geocoding** para obtener coordenadas.
7. 📊 Los datos se agregan a un archivo Excel existente en el **bucket de salida**.
8. 🌍 Luego puedes generar un mapa con esos resultados.

---

## ✨ Características Destacadas

- ⚡ **Procesamiento automático** al subir archivos.
- 🧾 Soporte para archivos `.txt` y `.pdf`.
- 📍 **Geolocalización con precisión** mediante Google Maps.
- 🔁 **Resultados acumulativos** en un único archivo Excel.
- 🔐 Gestión segura de claves con Parameter Store.
- 🌐 Opción de **visualización de resultados en mapa**.

---

## 🚀 Guía de Despliegue

### 1. Requisitos Previos

- Cuenta de AWS con permisos para crear Lambdas, Buckets, Roles, y Parámetros.
- Clave API de Google Maps con la **Geocoding API** habilitada.

---

### 2. Guardar la Clave API de Google

1. Abre **AWS Systems Manager** → **Parameter Store**.
2. Crea un parámetro:
   - **Nombre:** `/wenia/google_api_key`
   - **Tipo:** `SecureString`
   - **Valor:** tu clave API de Google.

---

### 3. Crear la Capa Personalizada (Lambda Layer)

```bash
mkdir -p capa_pequena/python
pip install "thefuzz[speedup]" requests openpyxl -t capa_pequena/python
Compress-Archive -Path .\capa_pequena\python\* -DestinationPath capa_thefuzz.zip
Ve a AWS Lambda → Capas → Crear capa.
Nombre: CapaTheFuzz.
Subir el archivo capa_thefuzz.zip.
Compatible con Python 3.12 y arquitectura x86_64.
⚠️ La capa debe contener la carpeta python/ en el nivel raíz del ZIP.


---

### 4. Crear los Buckets S3
entradas-direcciones-tuProyecto
resultados-direcciones-tuProyecto

---

### 5.Crear un Rol IAM para Lambda
Abre IAM → Roles → Crear rol.
Tipo de entidad confiable: Lambda.
Adjunta las siguientes políticas:
AWSLambdaBasicExecutionRole
AmazonS3FullAccess
AmazonTextractFullAccess
AmazonSSMReadOnlyAccess

---

### 6.Crear la Función Lambda
Nombre: procesador-direcciones-v2
Tiempo de ejecución: Python 3.12
Rol: el creado en el paso anterior
Subir el código
Comprime tu lambda_function.py en un archivo .zip.
Súbelo como código fuente de la función.
Añadir Capas
AWSSDKPandas-Python312 (desde AWS)
CapaTheFuzz (creada por ti)
Variables de entorno
OUTPUT_BUCKET: nombre del bucket de salida
OUTPUT_FILE_KEY: resultados_acumulados.xlsx
Timeout
Ajustar a 3 minutos

---

### 7.Añadir el Disparador
En la página de tu Lambda, haz clic en "Añadir disparador".
Selecciona S3, elige el bucket de entrada y guarda.

🧪 Cómo Usar el Sistema
Sube un archivo .txt o .pdf al bucket de entrada.
Espera ~1-3 minutos mientras Lambda lo procesa.
Abre el bucket de salida y descarga resultados_acumulados.xlsx.

🌍 Generar el Mapa
Una vez descargado el Excel, ejecuta este script local:

bash
Copiar
Editar
python crear_mapa.py

Esto generará un archivo mapa_final.html que puedes abrir en tu navegador para visualizar los puntos en el mapa.