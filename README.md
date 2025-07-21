# Proyecto de Procesamiento y Geolocalización de Direcciones

Este proyecto es un conjunto de scripts de Python diseñados para leer direcciones desde una fuente de datos, encontrar variantes lógicas, enriquecerlas con coordenadas geográficas a través de la API de Google y visualizarlas en un mapa.

## Características

-   Lee una o más direcciones base desde un archivo en un bucket de AWS S3.
-   Genera variantes lógicas de las nomenclaturas de direcciones (ej. CRA -> Carrera, Kra, etc.).
-   Compara las variantes con la dirección original y selecciona las que tienen una similitud mayor al 90%, priorizando las coincidencias perfectas (100%).
-   Utiliza la API de Google Geocoding para obtener las coordenadas (latitud y longitud) de las direcciones válidas.
-   Almacena los resultados enriquecidos en un archivo Excel.
-   Genera un mapa HTML interactivo con marcadores para cada dirección geolocalizada.

## Requisitos Previos

-   Python 3.8 o superior.
-   Una cuenta de AWS con credenciales configuradas localmente (vía `aws configure`).
-   Una clave de API de Google Maps Platform con la **Geocoding API** habilitada.

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/](https://github.com/)<tu-usuario>/<tu-repositorio>.git
    cd <tu-repositorio>
    ```

2.  **Crear el archivo de configuración:**
    Crea un archivo llamado `config.json` en la raíz del proyecto y copia la siguiente estructura.
    ```json
    {
        "s3_bucket_output": "tu-bucket-de-s3",
        "s3_key_original": "tu-archivo-de-direcciones.txt",
        "excel_output_file": "output/resultados_enriquecidos.xlsx",
        "map_output_file": "output/mapa_de_direcciones.html",
        "google_api_key": "TU_CLAVE_DE_API_SECRETA_DE_GOOGLE"
    }
    ```
    **IMPORTANTE:** Reemplaza los valores con los de tu configuración. Este archivo no debe ser compartido públicamente (asegúrate de que esté en tu `.gitignore`).

3.  **Instalar las dependencias:**
    Ejecuta el siguiente comando para instalar todas las bibliotecas necesarias.
    ```bash
    pip install -r requirements.txt
    ```

## Uso

El proceso se ejecuta en dos pasos desde la consola:

1.  **Procesar datos y obtener coordenadas:**
    Este comando leerá el archivo de S3, lo procesará y creará el archivo Excel con las coordenadas dentro de la carpeta `output/`.
    ```bash
    python procesador_completo.py
    ```

2.  **Generar el mapa:**
    Una vez que tengas el archivo Excel, ejecuta este comando para crear el mapa.
    ```bash
    python crear_mapa.py
    ```
    El resultado será un archivo `mapa_de_direcciones.html` dentro de la carpeta `output/` que puedes abrir en tu navegador.