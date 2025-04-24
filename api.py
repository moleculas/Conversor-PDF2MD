from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import PlainTextResponse, JSONResponse
import tempfile
import os
import uuid
import json
from process_pdf import process_pdf_to_markdown
from typing import Dict, Optional, List, Union
import threading
import time
import logging
import queue
from collections import deque

app = FastAPI()

# Directorio para almacenar trabajos
JOBS_DIR = os.environ.get("JOBS_DIR", "/app/jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

# Estructura para almacenar información de trabajos en memoria
# Estructura de un trabajo:
# - id: str (UUID)
# - status: str ("pending", "processing", "completed", "error")
# - message: str (mensaje de error o info adicional)
# - pdf_path: str (ruta al PDF original)
# - md_path: str (ruta al archivo Markdown generado)
# - created_at: float (timestamp de creación)
# - updated_at: float (timestamp de última actualización)
# - result: Optional[str] (contenido Markdown si está completado)
# - params: Dict (parámetros de configuración)
jobs: Dict[str, Dict] = {}

# Diccionario para almacenar logs por job_id
job_logs = {}  # Diccionario para almacenar logs por job_id
MAX_LOG_ENTRIES = 100  # Número máximo de entradas de log por trabajo

def log_to_job(job_id, message, level="INFO"):
    """Añade un mensaje de log al registro del trabajo específico."""
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Inicializar la cola de logs si no existe
    if job_id not in job_logs:
        job_logs[job_id] = deque(maxlen=MAX_LOG_ENTRIES)
    
    # Añadir entrada de log
    job_logs[job_id].append(log_entry)
    
    # También imprimir en la consola para debugging
    print(f"[Job {job_id}] {log_entry}")
    
    return log_entry

def save_job_state(job_id: str):
    """Guarda el estado del trabajo en disco para persistencia."""
    job_data = jobs[job_id].copy()
    
    # Eliminamos el resultado del contenido a guardar si es muy grande
    if 'result' in job_data and job_data['result'] and len(job_data['result']) > 100:
        job_data['result'] = "STORED_SEPARATELY"  # Marcador
        
        # Guardar resultado en archivo separado
        result_path = os.path.join(JOBS_DIR, f"{job_id}_result.txt")
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(jobs[job_id]['result'])
    
    # Guardar metadatos del trabajo
    job_path = os.path.join(JOBS_DIR, f"{job_id}.json")
    with open(job_path, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, ensure_ascii=False)

def load_job_state(job_id: str) -> Optional[Dict]:
    """Carga el estado del trabajo desde disco."""
    job_path = os.path.join(JOBS_DIR, f"{job_id}.json")
    
    if not os.path.exists(job_path):
        return None
    
    with open(job_path, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    # Recuperar resultado de archivo separado si es necesario
    if job_data.get('result') == "STORED_SEPARATELY":
        result_path = os.path.join(JOBS_DIR, f"{job_id}_result.txt")
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                job_data['result'] = f.read()
    
    return job_data

def process_job(job_id: str):
    """Procesa un trabajo en segundo plano."""
    # Actualizar estado
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["updated_at"] = time.time()
    save_job_state(job_id)
    
    # Obtener parámetros
    params = jobs[job_id].get("params", {})
    dpi = params.get("dpi", 300)
    conf_threshold = params.get("conf_threshold", 60)
    lang = params.get("lang", "spa")
    area = params.get("area", None)
    
    # Registrar inicio del procesamiento
    log_to_job(job_id, "Iniciando procesamiento del documento PDF")
    log_to_job(job_id, f"Configuración: DPI={dpi}, LANG={lang}, THRESHOLD={conf_threshold}")
    if area:
        log_to_job(job_id, f"Procesando área específica: {area}")
    
    # Recuperar información del trabajo
    pdf_path = jobs[job_id]["pdf_path"]
    md_path = jobs[job_id]["md_path"]
    
    try:
        # Registrar información sobre el PDF
        log_to_job(job_id, f"Documento recibido: {os.path.basename(pdf_path)}")
        
        # Intentar obtener información del PDF
        try:
            # Intentamos importar PyPDF2 o PyPDF4 según esté disponible
            pdf_module = None
            try:
                import PyPDF2
                pdf_module = PyPDF2
                log_to_job(job_id, "Utilizando PyPDF2 para análisis del documento")
            except ImportError:
                try:
                    import PyPDF4
                    pdf_module = PyPDF4
                    log_to_job(job_id, "Utilizando PyPDF4 para análisis del documento")
                except ImportError:
                    log_to_job(job_id, "No se pudo importar librería para análisis PDF", "WARNING")
            
            if pdf_module:
                with open(pdf_path, 'rb') as pdf_file:
                    try:
                        pdf_reader = pdf_module.PdfReader(pdf_file)
                        num_pages = len(pdf_reader.pages)
                        log_to_job(job_id, f"El documento tiene {num_pages} páginas")
                    except Exception as e:
                        log_to_job(job_id, f"No se pudo determinar el número de páginas: {str(e)}", "WARNING")
        except Exception as e:
            log_to_job(job_id, f"Error al analizar la estructura del PDF: {str(e)}", "WARNING")
        
        # Registrar inicio de OCR
        log_to_job(job_id, "Iniciando proceso de OCR (reconocimiento óptico de caracteres)")
        
        # Definir función de callback para los logs
        def log_callback(message):
            return log_to_job(job_id, message)
        
        # Llamamos a la función real de procesamiento con el callback
        process_pdf_to_markdown(
            input_pdf=pdf_path,
            output_md=md_path,
            dpi=dpi,
            lang=lang,
            conf_threshold=conf_threshold,
            area=area,
            log_callback=log_callback
        )
        
        # Leer contenido del Markdown generado
        with open(md_path, "r", encoding="utf-8") as md_file:
            md_content = md_file.read()
        
        # Actualizar el job con el resultado
        log_to_job(job_id, "Proceso completado exitosamente")
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = md_content
        jobs[job_id]["updated_at"] = time.time()
        save_job_state(job_id)
        
    except Exception as e:
        # En caso de error
        error_msg = str(e)
        log_to_job(job_id, f"Error durante el procesamiento: {error_msg}", "ERROR")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = error_msg
        jobs[job_id]["updated_at"] = time.time()
        save_job_state(job_id)
        
        # Limpieza en caso de error, pero sólo si no estamos en debug
        if os.environ.get("DEBUG") != "1":
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
                log_to_job(job_id, "Eliminado archivo PDF temporal", "INFO")
            if os.path.exists(md_path):
                os.unlink(md_path)
                log_to_job(job_id, "Eliminado archivo MD temporal", "INFO")

@app.post("/process", response_class=JSONResponse)
async def process_pdf(
    file: UploadFile = File(...),
    dpi: int = Form(300),
    conf_threshold: int = Form(60),
    lang: str = Form("spa"),
    area: Optional[str] = Form(None)
):
    """Inicia un nuevo trabajo de procesamiento de PDF."""
    # Generar ID único para el trabajo
    job_id = str(uuid.uuid4())
    
    # Crear archivos temporales para la entrada y salida
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=JOBS_DIR) as pdf_file:
        # Guardar el PDF subido
        content = await file.read()
        pdf_file.write(content)
        pdf_path = pdf_file.name
    
    # Preparar nombre para archivo de salida
    md_path = pdf_path.replace(".pdf", ".md")
    
    # Procesar el área si existe
    area_coords = None
    if area:
        try:
            # Convertir la cadena de área a lista de enteros
            if isinstance(area, str):
                area_coords = json.loads(area)
            if isinstance(area_coords, list) and len(area_coords) == 4:
                area_coords = tuple(int(coord) for coord in area_coords)
            else:
                area_coords = None
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            # En caso de error, log pero continuar sin área
            print(f"Error al procesar área: {e}")
    
    # Crear el registro del trabajo con los parámetros
    job_info = {
        "id": job_id,
        "status": "pending",
        "message": "",
        "pdf_path": pdf_path,
        "md_path": md_path,
        "created_at": time.time(),
        "updated_at": time.time(),
        "result": None,
        "params": {
            "dpi": dpi,
            "conf_threshold": conf_threshold,
            "lang": lang,
            "area": area_coords
        }
    }
    
    # Guardar info del trabajo
    jobs[job_id] = job_info
    save_job_state(job_id)
    
    # Iniciar procesamiento en segundo plano
    thread = threading.Thread(target=process_job, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    # Devolver el ID del trabajo inmediatamente
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Procesamiento iniciado. Consulte el estado con el endpoint /status/{job_id}"
    }

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Consulta el estado de un trabajo por su ID."""
    # Buscar el trabajo en memoria
    job = jobs.get(job_id)
    
    # Si no está en memoria, intentar cargarlo desde disco
    if not job:
        job = load_job_state(job_id)
        if job:
            # Si lo encontramos en disco, lo cargamos en memoria
            jobs[job_id] = job
    
    # Si no lo encontramos, devolver error
    if not job:
        raise HTTPException(status_code=404, detail=f"Trabajo con ID {job_id} no encontrado")
    
    # Respuesta base
    response = {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"]
    }
    
    # Añadir mensaje si existe
    if job.get("message"):
        response["message"] = job["message"]
    
    # Añadir parámetros
    if job.get("params"):
        response["params"] = job["params"]
    
    # Si está completado, añadimos el contenido Markdown
    if job["status"] == "completed" and job.get("result"):
        response["result"] = job["result"]
    
    return response

@app.get("/result/{job_id}", response_class=PlainTextResponse)
async def get_job_result(job_id: str):
    """Devuelve sólo el resultado Markdown de un trabajo completado."""
    # Buscar el trabajo
    job = jobs.get(job_id)
    
    # Si no está en memoria, intentar cargarlo desde disco
    if not job:
        job = load_job_state(job_id)
        if job:
            jobs[job_id] = job
    
    # Si no lo encontramos, devolver error
    if not job:
        raise HTTPException(status_code=404, detail=f"Trabajo con ID {job_id} no encontrado")
    
    # Si no está completado, devolver error
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"El trabajo aún no está completado (estado actual: {job['status']})"
        )
    
    # Devolver el resultado
    if not job.get("result"):
        raise HTTPException(status_code=500, detail="El trabajo está marcado como completado pero no tiene resultado")
    
    return job["result"]

@app.get("/logs/{job_id}")
async def get_job_logs(job_id: str, last_n: int = None):
    """Devuelve los logs del proceso para un trabajo específico."""
    if job_id not in job_logs:
        # Si no hay logs, devolvemos una lista vacía
        return {"logs": []}
    
    logs = list(job_logs[job_id])
    
    # Si se solicita solo los últimos N logs
    if last_n is not None and last_n > 0:
        logs = logs[-last_n:]
    
    return {"logs": logs}

# Endpoint para limpiar trabajos antiguos (podría protegerse con autenticación en producción)
@app.post("/cleanup")
async def cleanup_old_jobs(days: int = 1):
    """Elimina trabajos más antiguos que el número de días especificado."""
    now = time.time()
    seconds = days * 24 * 60 * 60
    
    removed = 0
    for job_id in list(jobs.keys()):
        if now - jobs[job_id]["created_at"] > seconds:
            # Eliminar archivos asociados
            pdf_path = jobs[job_id].get("pdf_path")
            md_path = jobs[job_id].get("md_path")
            
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            if md_path and os.path.exists(md_path):
                os.unlink(md_path)
                
            # Eliminar archivos de estado
            job_path = os.path.join(JOBS_DIR, f"{job_id}.json")
            result_path = os.path.join(JOBS_DIR, f"{job_id}_result.txt")
            
            if os.path.exists(job_path):
                os.unlink(job_path)
            if os.path.exists(result_path):
                os.unlink(result_path)
            
            # Eliminar de memoria
            del jobs[job_id]
            # También eliminar los logs
            if job_id in job_logs:
                del job_logs[job_id]
            removed += 1
    
    return {"message": f"Se eliminaron {removed} trabajos antiguos"}

if __name__ == "__main__":
    import uvicorn
    
    # Cargar trabajos existentes al iniciar
    if os.path.exists(JOBS_DIR):
        for filename in os.listdir(JOBS_DIR):
            if filename.endswith(".json"):
                job_id = filename.replace(".json", "")
                job_data = load_job_state(job_id)
                if job_data:
                    jobs[job_id] = job_data
    
    # Iniciar el servidor
    uvicorn.run(app, host="0.0.0.0", port=5001)