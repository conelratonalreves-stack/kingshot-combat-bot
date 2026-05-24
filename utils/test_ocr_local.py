import pytesseract
from PIL import Image
from utils.ocr_extractor import extract_battle_report_stats
import re
import json
import sys


def run_tesseract_bytes(image_bytes, langs='spa+eng'):
    img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(img, lang=langs)
    return text


def run_tesseract_path(path, langs='spa+eng'):
    img = Image.open(path)
    text = pytesseract.image_to_string(img, lang=langs)
    return text


def extract_numbers(text):
    # regex for percentages and numbers with commas/dots
    nums = re.findall(r"[-+]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?%?", text)
    return nums


def test_file_paths(paths):
    for path in paths:
        print('\n' + '='*60)
        print('TESTING:', path)
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except FileNotFoundError:
            print('File not found:', path)
            continue

        print('\n--- OCR raw (spa+eng) ---')
        try:
            raw = run_tesseract_path(path, langs='spa+eng')
            print(raw)
        except Exception as e:
            print('Error running tesseract on path:', e)

        print('\n--- Numbers found (regex) ---')
        try:
            nums = extract_numbers(raw)
            print(nums)
        except Exception as e:
            print('Error extracting numbers:', e)

        print('\n--- extract_battle_report_stats() output ---')
        try:
            parsed = extract_battle_report_stats(data)
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception as e:
            print('Error running extract_battle_report_stats:', e)


if __name__ == '__main__':
    import io
    paths = [
        'data/test_top.png',
        'data/test_bottom.png'
    ]
    # allow override via CLI
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    test_file_paths(paths)
