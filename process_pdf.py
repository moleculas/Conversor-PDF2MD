import argparse
import os
import sys
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from pytesseract import Output

def ocr_impreso_con_placeholder(img: Image.Image, conf_threshold: int = 60, log_callback = None) -> str:
    """
    Aplica OCR a una imagen, devuelve un texto donde:
    - Se mantienen las palabras con conf >= conf_threshold.
    - Si una línea está compuesta solo por palabras con conf < threshold,
      se sustituye por '[texto manuscrito]'.
    """
    def log(message):
        if log_callback:
            log_callback(message)
    
    log("Aplicando OCR al fragmento de imagen...")
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    n = len(data['level'])
    log(f"OCR completado. Se detectaron {n} elementos")
    
    lines = []
    current_line = 1
    buffer = []
    manuscrito = False
    
    detected_text = 0
    detected_manuscript = 0
    
    for i in range(n):
        line_num = data['line_num'][i]
        txt = data['text'][i].strip()
        try:
            conf = int(data['conf'][i])
        except (ValueError, TypeError):
            conf = -1

        # Cuando cambia de línea, volcamos el buffer o el placeholder
        if line_num != current_line:
            if buffer:
                lines.append(' '.join(buffer))
                detected_text += 1
            elif manuscrito:
                lines.append('[texto manuscrito]')
                detected_manuscript += 1
            buffer = []
            manuscrito = False
            current_line = line_num

        if not txt:
            continue

        if conf >= conf_threshold:
            buffer.append(txt)
        else:
            manuscrito = True

    # Flush de la última línea
    if buffer:
        lines.append(' '.join(buffer))
        detected_text += 1
    elif manuscrito:
        lines.append('[texto manuscrito]')
        detected_manuscript += 1

    log(f"Análisis completado. Se detectaron {detected_text} líneas de texto impreso y {detected_manuscript} fragmentos manuscritos")
    return '\n'.join(lines)

def process_pdf_to_markdown(input_pdf: str,
                           output_md: str,
                           dpi: int = 300,
                           lang: str = 'spa',
                           conf_threshold: int = 60,
                           area: tuple = None,
                           log_callback = None):
    """
    Convierte cada página de un PDF en imagen, extrae el texto impreso
    y genera un .md con marcadores para manuscritos.
    """
    # Si hay una función de log, la usamos
    def log(message):
        if log_callback:
            log_callback(message)
        print(message)  # También imprimimos en consola
    
    log(f"Iniciando conversión del PDF {os.path.basename(input_pdf)}")
    
    # convierte PDF a imágenes
    log("Convirtiendo PDF a imágenes...")
    images = convert_from_path(input_pdf, dpi=dpi)
    log(f"PDF convertido a {len(images)} imágenes")

    with open(output_md, 'w', encoding='utf-8') as md:
        for page_num, img in enumerate(images, start=1):
            log(f"Procesando página {page_num}/{len(images)}")
            
            # Si se pasa un área (left, upper, right, lower), recortamos
            if area:
                log(f"Recortando área específica: {area}")
                img = img.crop(area)

            md.write(f'## Página {page_num}\n\n')
            
            # Extraemos texto con placeholders
            log(f"Aplicando OCR a la página {page_num}...")
            texto = ocr_impreso_con_placeholder(img, conf_threshold=conf_threshold)
            log(f"OCR completado para página {page_num}")
            
            # Escapamos líneas vacías
            for line in texto.split('\n'):
                md.write(line + '\n')
            md.write('\n---\n\n')
    
    log(f"Procesamiento completado. Archivo Markdown generado: {os.path.basename(output_md)}")

def parse_args():
    parser = argparse.ArgumentParser(
        description='OCR avanzado: texto impreso + marcadores para manuscrito')
    parser.add_argument('input_pdf', help='PDF de entrada')
    parser.add_argument('output_md', help='Archivo Markdown de salida')
    parser.add_argument('--dpi', type=int, default=300,
                        help='Resolución en DPI para el renderizado (por defecto: 300)')
    parser.add_argument('--lang', default='spa',
                        help='Código de idioma para Tesseract (por defecto: spa)')
    parser.add_argument('--conf-threshold', type=int, default=60,
                        help='Umbral de confianza para considerar texto impreso (0–100)')
    parser.add_argument('--area', nargs=4, type=int, metavar=('L','U','R','B'),
                        help='Área para recortar cada página (left upper right bottom)')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    # Configurar Tesseract
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'
    # 'lang' y posibles config extra
    tess_config = f'-l {args.lang} --psm 1 --oem 3'

    # Si quieres pasar la configuración global
    pytesseract.pytesseract.run_and_get_output  # noqa: ensure library is loaded

    area = tuple(args.area) if args.area else None

    try:
        process_pdf_to_markdown(
            input_pdf=args.input_pdf,
            output_md=args.output_md,
            dpi=args.dpi,
            lang=args.lang,
            conf_threshold=args.conf_threshold,
            area=area
        )
        print(f'OCR completado. Markdown generado en {args.output_md}')
    except Exception as e:
        print(f'Error durante el procesamiento: {e}', file=sys.stderr)
        sys.exit(1)
