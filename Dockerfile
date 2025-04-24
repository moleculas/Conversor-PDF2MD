# Paso 1: Imagen base ligera de Python
FROM python:3.11-slim

# Paso 2: Variables de entorno para codificación y logs
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1

# Paso 3: Instalar dependencias de sistema y OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    ghostscript \
    qpdf \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Paso 4: Directorio de trabajo
WORKDIR /app

# Paso 5: Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Paso 6: Copiar código restante
COPY . .

# Paso 7: Comando por defecto al iniciar
CMD ["python", "api.py"]