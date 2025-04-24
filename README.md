# PDF2MD

## Descripción
PDF2MD es una aplicación web que convierte archivos PDF a formato Markdown mediante OCR (Reconocimiento Óptico de Caracteres). La aplicación distingue automáticamente entre texto impreso y manuscrito basándose en el nivel de confianza del OCR, marcando las áreas de baja confianza como "[texto manuscrito]".

## Características principales
- Conversión eficiente de PDF a Markdown con OCR integrado
- Distinción automática entre texto impreso y texto manuscrito
- Interfaz web intuitiva con visualización de resultados en tiempo real
- Sistema de procesamiento asincrónico con seguimiento de trabajos
- Visualización de logs de procesamiento en tiempo real
- Opciones de configuración avanzadas:
  - Control de resolución (DPI)
  - Ajuste del umbral de confianza para detección de texto manuscrito
  - Selección de idioma (español, inglés, francés, etc.)
  - Procesamiento de áreas específicas del PDF

## Tecnologías utilizadas
- **Backend**: Python con FastAPI y Tesseract OCR
- **Frontend**: HTML, CSS (Tailwind CSS), JavaScript
- **Procesamiento**: pytesseract, pdf2image, OpenCV
- **Contenerización**: Docker y Docker Compose
- **Fuente tipográfica**: Satoshi

## Requisitos del sistema
- Docker Desktop
- Navegador web moderno
- 4GB de RAM mínimo (recomendado 8GB para PDFs grandes)
- Espacio en disco para archivos generados

## Instalación y Ejecución Rápida
1. Asegúrate de tener Docker Desktop instalado y en ejecución
2. Descarga el proyecto:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd pdf2md
   ```

3. Inicia la aplicación:
   ```bash
   docker-compose up
   ```

4. Accede a la aplicación en tu navegador: [http://localhost:8000](http://localhost:8000)

## Inicio rápido (script automático)
Puedes usar el script `start_pdf2md.bat` para iniciar automáticamente la aplicación:
1. Ejecuta `start_pdf2md.bat` haciendo doble clic
2. El script verificará si Docker está disponible
3. Iniciará los contenedores y abrirá automáticamente el navegador

## Guía de uso
1. **Subir archivo**: Haz clic en el área de subida o arrastra un archivo PDF.
2. **Configurar opciones** (opcional):
   - Ajusta la resolución (DPI) para mejor calidad a costa de velocidad
   - Configura el umbral de confianza según la calidad de tu documento
   - Selecciona el idioma del documento
   - Define un área específica para procesar solo una parte del PDF
3. **Convertir**: Haz clic en "Convertir a Markdown"
4. **Seguimiento**: Observa el progreso en tiempo real con los logs del proceso
5. **Descargar resultado**: Una vez completado, descarga el archivo Markdown generado

## Estructura del proyecto
```
pdf2md/
├── api.py                   # API REST del servicio transcriber
├── process_pdf.py           # Lógica de OCR y procesamiento PDF
├── docker-compose.yml       # Configuración de servicios Docker
├── Dockerfile               # Configuración del servicio transcriber
├── Dockerfile.web           # Configuración del servicio web
├── requirements.txt         # Dependencias del servicio transcriber
├── web/                     # Carpeta del servicio web
│   ├── app.py               # Aplicación web (FastAPI)
│   ├── templates/           # Plantillas HTML
│   │   ├── index.html       # Página principal
│   │   ├── track.html       # Página de seguimiento
│   │   ├── result.html      # Página de resultados
│   │   └── error.html       # Página de error
│   ├── static/              # Archivos estáticos (CSS, JS)
│   └── requirements.txt     # Dependencias del servicio web
├── jobs/                    # Carpeta para almacenar trabajos
├── input/                   # Carpeta para archivos de entrada
└── output/                  # Carpeta para archivos de salida
```

## Solución de problemas
- **Docker no está disponible**: Asegúrate de que Docker Desktop esté instalado y en ejecución.
- **Timeout en procesamiento**: Los PDF grandes o complejos pueden tomar más tiempo. La aplicación espera hasta completar el procesamiento.
- **Detección incorrecta de texto manuscrito**: Ajusta el umbral de confianza en las opciones avanzadas para mejorar la detección.
- **Error en la detección de idioma**: Selecciona manualmente el idioma correcto en las opciones avanzadas.

## Limitaciones conocidas
- Actualmente no soporta procesamiento paralelo de múltiples documentos
- El procesamiento de imágenes con baja calidad puede resultar en una detección imprecisa
- Documentos muy grandes (>100 páginas) pueden consumir muchos recursos

## Desarrollo y contribuciones
¡Las contribuciones son bienvenidas! Si deseas mejorar PDF2MD:
1. Haz un fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## Licencia
Este proyecto está bajo la licencia MIT.