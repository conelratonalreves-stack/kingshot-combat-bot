"""
OCR extractor para ranking usando EasyOCR.
100% gratis, local, sin APIs - Mejor que Tesseract.
"""

from typing import List, Dict, Optional
import io
import re

# Inicializar EasyOCR (se carga una sola vez)
print("[OCR Init] Cargando EasyOCR...")
try:
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    USE_EASYOCR = True
    print("[OCR Init] ✓ EasyOCR cargado")
except Exception as e:
    print(f"[OCR Init] ⚠ Error cargando EasyOCR: {e}")
    USE_EASYOCR = False


def extract_ranking_entries_easyocr(image_bytes: bytes) -> List[Dict]:
    """Extrae entradas del ranking usando EasyOCR."""
    print(f"[EasyOCR] Procesando imagen de {len(image_bytes)} bytes")
    
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        
        # EasyOCR trabaja mejor con numpy array
        import numpy as np
        img_array = np.array(img)
        
        print("[EasyOCR] Ejecutando OCR...")
        result = reader.readtext(img_array)
        
        # result es lista de (bbox, text, confidence)
        # Ordenar por posición vertical (Y)
        sorted_results = sorted(result, key=lambda x: x[0][0][1])
        
        print(f"[EasyOCR] Detectados {len(sorted_results)} bloques de texto")
        
        # Agrupar textos por línea (similar Y)
        lines = []
        current_line = []
        last_y = -1
        threshold = 30  # píxeles de tolerancia vertical
        
        for bbox, text, conf in sorted_results:
            y = bbox[0][1]
            if last_y == -1 or abs(y - last_y) < threshold:
                current_line.append(text)
                last_y = y
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [text]
                last_y = y
        
        if current_line:
            lines.append(' '.join(current_line))
        
        print(f"[EasyOCR] Agrupado en {len(lines)} líneas")
        
        # Parsear cada línea para extraer: rank [TAG]Nombre score
        entries = []
        pattern = r'(\d{1,3})\s*\[([A-Z0-9]{2,5})\]\s*(.+?)\s+(\d{3,6})\s*$'
        
        for line in lines:
            line = line.strip().upper()  # EasyOCR a veces da minúsculas
            if not line:
                continue
            
            # Intentar patrón completo
            match = re.search(pattern, line)
            if match:
                rank = int(match.group(1))
                if 1 <= rank <= 100:
                    entries.append({
                        'rank': rank,
                        'alliance': match.group(2).upper(),
                        'name': match.group(3).strip(),
                        'score': int(match.group(4))
                    })
                    continue
            
            # Fallback: buscar rank + tag al menos
            m = re.search(r'(\d{1,3})\s*\[([A-Z0-9]{2,5})\](.+)', line)
            if m:
                rank = int(m.group(1))
                if 1 <= rank <= 100:
                    rest = m.group(3).strip()
                    score_match = re.search(r'(\d{3,6})\s*$', rest)
                    score = int(score_match.group(1)) if score_match else None
                    name = re.sub(r'\s*\d{3,6}\s*$', '', rest).strip()
                    
                    entries.append({
                        'rank': rank,
                        'alliance': m.group(2).upper(),
                        'name': name if name else 'Unknown',
                        'score': score
                    })
        
        print(f"[EasyOCR] ✓ Extraídas {len(entries)} entradas")
        entries.sort(key=lambda e: e['rank'])
        return entries[:9]
        
    except Exception as e:
        print(f"[EasyOCR] ✗ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def extract_ranking_entries_tesseract(image_bytes: bytes) -> List[Dict]:
    """Fallback: OCR tradicional con Tesseract (menos preciso)."""
    from PIL import Image, ImageOps, ImageEnhance
    import pytesseract
    import re
    
    # Preprocesamiento básico
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((int(img.width * 2), int(img.height * 2)), Image.LANCZOS)
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)
    
    # OCR simple
    text = pytesseract.image_to_string(img, lang='eng', config='--psm 6')
    
    # Extraer filas con regex
    entries = []
    pattern = r'(\d{1,3})\s+\[([A-Za-z0-9]{2,5})\]\s*(.+?)\s+(\d{2,6})'
    
    for match in re.finditer(pattern, text):
        rank = int(match.group(1))
        if 1 <= rank <= 100:
            entries.append({
                'rank': rank,
                'alliance': match.group(2).upper(),
                'name': match.group(3).strip(),
                'score': int(match.group(4))
            })
    
    return entries[:9]


def extract_ranking_entries(image_bytes: bytes) -> List[Dict]:
    """Punto de entrada principal: usa Google Cloud Vision si está disponible, sino Tesseract."""
    print(f"[OCR] USE_VISION_API = {USE_VISION_API}")
    
    if USE_VISION_API:
        print("[OCR] Usando Google Cloud Vision API")
        result = extract_ranking_entries_google(image_bytes)
        if len(result) > 0:
            return result
        # Si Google falla, caer a Tesseract
        print("[OCR] Google no retornó datos, fallback a Tesseract")
    else:
        print("[OCR] Usando Tesseract (fallback)")
    
    return extract_ranking_entries_tesseract(image_bytes)
