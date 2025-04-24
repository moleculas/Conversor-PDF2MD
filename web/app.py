import os
import uuid
import httpx
import time
import json
from urllib.parse import urljoin

from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional

app = FastAPI()

# Cargamos la plantilla
templates = Jinja2Templates(directory="templates")

# Directorio de subida dentro del contenedor
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Variable de entorno para la URL del OCR
OCR_URL = os.getenv("OCR_URL", "http://transcriber:5001/process")
STATUS_URL_BASE = os.getenv("STATUS_URL_BASE", "http://transcriber:5001/status/")
RESULT_URL_BASE = os.getenv("RESULT_URL_BASE", "http://transcriber:5001/result/")
LOGS_URL_BASE = os.getenv("LOGS_URL_BASE", "http://transcriber:5001/logs/")

# Montamos el directorio de uploads para servir los .md
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Montamos el directorio de estáticos para CSS, JS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Diccionario para almacenar los trabajos en proceso
active_jobs = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert")
async def convert(
    request: Request, 
    pdf: UploadFile = File(...),
    dpi: int = Form(300),
    conf_threshold: int = Form(60),
    lang: str = Form("spa"),
    process_areas: bool = Form(False),
    area_left: Optional[int] = Form(0),
    area_top: Optional[int] = Form(0),
    area_right: Optional[int] = Form(0),
    area_bottom: Optional[int] = Form(0)
):
    # 1) Guardamos el PDF en disco con un nombre único
    original_filename = pdf.filename  # Guardar el nombre original del archivo
    pdf_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
    with open(pdf_path, "wb") as f:
        f.write(await pdf.read())

    # 2) Preparamos los parámetros adicionales
    params = {
        "dpi": dpi,
        "conf_threshold": conf_threshold,
        "lang": lang,
        "original_filename": original_filename  # Añadimos el nombre original
    }
    
    # Añadir área si está habilitada
    if process_areas and area_right > 0 and area_bottom > 0:
        params["area"] = json.dumps([area_left, area_top, area_right, area_bottom])

    # 3) Enviamos el PDF al servicio OCR para iniciar el procesamiento
    async with httpx.AsyncClient(timeout=30.0) as client:
        files = {"file": (pdf_filename, open(pdf_path, "rb"), "application/pdf")}
        resp = await client.post(OCR_URL, files=files, data=params)
        resp.raise_for_status()
        data = resp.json()
    
    # 4) Guardamos el ID del trabajo y redirigimos a la página de seguimiento
    job_id = data.get("job_id")
    if not job_id:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "No se pudo iniciar el procesamiento"
            }
        )
    
    # Guardar en el diccionario de trabajos activos
    active_jobs[job_id] = {
        "pdf_filename": pdf_filename,
        "original_filename": original_filename,  # Guardamos el nombre original
        "pdf_path": pdf_path,
        "status": "pending",
        "created_at": time.time(),
        "params": params
    }
    
    # Redirigir a la página de seguimiento
    return RedirectResponse(url=f"/track/{job_id}", status_code=303)

@app.get("/track/{job_id}", response_class=HTMLResponse)
async def track_job(request: Request, job_id: str):
    """Página de seguimiento del trabajo que se actualizará con JavaScript."""
    return templates.TemplateResponse(
        "track.html",
        {
            "request": request,
            "job_id": job_id
        }
    )

@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Endpoint para que el frontend consulte el estado del trabajo."""
    try:
        status_url = urljoin(STATUS_URL_BASE, job_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(status_url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        return {"status": "error", "message": f"Error al consultar el estado: {str(e)}"}

@app.get("/api/logs/{job_id}")
async def proxy_job_logs(job_id: str, last_n: int = None):
    """Endpoint para que el frontend consulte los logs del trabajo."""
    try:
        logs_url = urljoin(LOGS_URL_BASE, job_id)
        params = {}
        if last_n is not None:
            params["last_n"] = last_n
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(logs_url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        return {"logs": [], "error": f"Error al consultar logs: {str(e)}"}

@app.get("/result/{job_id}", response_class=HTMLResponse)
async def show_result(request: Request, job_id: str):
    """Muestra la página de resultado cuando el trabajo está completo."""
    try:
        # Verificar estado del trabajo
        status_url = urljoin(STATUS_URL_BASE, job_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            status_resp = await client.get(status_url)
            status_resp.raise_for_status()
            job_data = status_resp.json()
        
        if job_data.get("status") != "completed":
            # Si no está completo, redirigir a la página de seguimiento
            return RedirectResponse(url=f"/track/{job_id}")
        
        # Si está completo, obtener el resultado
        result_url = urljoin(RESULT_URL_BASE, job_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            result_resp = await client.get(result_url)
            result_resp.raise_for_status()
            md_text = result_resp.text
        
        # Obtener parámetros utilizados (si están disponibles)
        params = job_data.get("params", {
            "dpi": 300,
            "conf_threshold": 60,
            "lang": "spa",
            "area": None
        })
        
        # Obtener el nombre original del archivo (si está disponible)
        original_filename = None
        if job_id in active_jobs:
            original_filename = active_jobs[job_id].get("original_filename")
        if not original_filename and params.get("original_filename"):
            original_filename = params.get("original_filename")
        
        # Generar nombre del archivo Markdown basado en el nombre original
        if original_filename:
            # Quitar la extensión .pdf si existe y añadir _convert.md
            if original_filename.lower().endswith('.pdf'):
                original_filename = original_filename[:-4]
            md_filename = f"{original_filename}_convert.md"
        else:
            # Si no tenemos el nombre original, usamos el ID del trabajo
            md_filename = f"{job_id}.md"
        
        # Guardar el markdown en disco para poder descargarlo luego
        md_path = os.path.join(UPLOAD_DIR, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        
        # Renderizar plantilla de resultado
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "markdown": md_text,
                "download_link": f"/download/{md_filename}",
                "params": params,
                "original_filename": original_filename
            },
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": f"Error al obtener el resultado: {str(e)}"
            }
        )

@app.get("/download/{md_filename}")
async def download(md_filename: str):
    """Endpoint para descargar el archivo Markdown."""
    md_path = os.path.join(UPLOAD_DIR, md_filename)
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Usar el parámetro 'attachment' para forzar la descarga en lugar de mostrar en el navegador
    return FileResponse(
        md_path,
        media_type="text/markdown",
        filename=md_filename,
        headers={"Content-Disposition": f"attachment; filename={md_filename}"}
    )