# PDF2MD

## Descripción
PDF2MD es una herramienta que convierte archivos PDF en archivos Markdown (MD). Utiliza OCR para extraer texto de PDFs y proporciona una interfaz web para cargar y visualizar los resultados.

## Características
- Conversión de PDF a Markdown.
- Soporte para OCR con Tesseract.
- Interfaz web simple para cargar y visualizar resultados.
- Backend desarrollado con FastAPI.
- Contenedorización con Docker.

## Requisitos previos
- Python 3.11 o superior.
- Docker y Docker Compose.

## Instalación
1. Clona este repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd pdf2md
   ```

2. Construye y ejecuta los contenedores con Docker Compose:
   ```bash
   docker-compose up --build
   ```

## Uso
1. Accede a la aplicación en tu navegador en `http://localhost:8000`.
2. Sube un archivo PDF para convertirlo a Markdown.

## Estructura del proyecto
- `input/`: Archivos PDF de entrada.
- `jobs/`: Resultados intermedios y finales.
- `output/`: Archivos procesados.
- `web/`: Código del frontend.
- `api.py`: Backend principal.
- `Dockerfile`: Configuración de Docker para el backend.
- `Dockerfile.web`: Configuración de Docker para el frontend.
- `docker-compose.yml`: Orquestación de contenedores.

## Contribuciones
¡Las contribuciones son bienvenidas! Por favor, abre un issue o un pull request para sugerir mejoras.

## Licencia
Este proyecto está bajo la licencia MIT.