"""
Test OCR con las capturas del ranking proporcionadas por el usuario.
"""
from utils.ocr_ranking import extract_ranking_entries
from pathlib import Path

# Usar las imágenes guardadas desde el chat
test_images = [
    r"c:\Bot Composicion Discord\test_ranking_1.jpg",
    r"c:\Bot Composicion Discord\test_ranking_2.jpg"
]

for img_path in test_images:
    p = Path(img_path)
    if not p.exists():
        print(f"❌ No encontrado: {img_path}")
        continue
    
    print(f"\n{'='*60}")
    print(f"📸 Procesando: {p.name}")
    print('='*60)
    
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    
    entries = extract_ranking_entries(img_bytes)
    
    if not entries:
        print("⚠️ No se detectaron entradas")
    else:
        print(f"✅ Detectadas {len(entries)} entradas:\n")
        for e in entries:
            score_str = str(e['score']) if e['score'] else '???'
            print(f"  #{e['rank']:3d}  [{e['alliance']:5s}] {e['name']:30s}  {score_str:>4s}")
