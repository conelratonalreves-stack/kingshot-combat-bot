"""
Script de prueba: OCR ranking con imagen en base64 o desde archivo.
"""
import sys
import base64
from utils.ocr_ranking import extract_ranking_entries

def test_with_file(filepath: str):
    """Prueba OCR con archivo de imagen."""
    print(f"\n{'='*70}")
    print(f"📸 Procesando: {filepath}")
    print('='*70)
    
    try:
        with open(filepath, 'rb') as f:
            img_bytes = f.read()
        
        entries = extract_ranking_entries(img_bytes)
        
        if not entries:
            print("⚠️ No se detectaron entradas")
            return
        
        print(f"✅ Detectadas {len(entries)} entradas:\n")
        print(f"{'Rank':<6} {'Tag':<8} {'Nombre':<35} {'Score':<8}")
        print('-' * 70)
        
        for e in entries:
            score_str = str(e['score']) if e['score'] is not None else '???'
            print(f"#{e['rank']:<5} [{e['alliance']:<5}]  {e['name']:<35} {score_str:>6}")
            
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {filepath}")
    except Exception as ex:
        print(f"❌ Error: {ex}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python test_ocr_ranking_file.py <imagen.jpg>")
        sys.exit(1)
    
    test_with_file(sys.argv[1])
