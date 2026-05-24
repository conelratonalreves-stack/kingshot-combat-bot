"""Test OCR with different configurations to find optimal settings."""

import pytesseract
from PIL import Image, ImageEnhance
import numpy as np
import sys

def preprocess_image(image, contrast=2.0, brightness=1.1, sharpness=2.0, threshold=160):
    """Preprocess with adjustable parameters."""
    if image.mode != 'L':
        image = image.convert('L')
    
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Sharpness(image).enhance(sharpness)
    
    arr = np.array(image)
    arr = np.where(arr > threshold, 255, 0).astype('uint8')
    image = Image.fromarray(arr)
    
    return image

def test_ocr_configs(image_path):
    """Test different OCR configurations."""
    print(f"\n{'='*80}")
    print(f"Testing OCR on: {image_path}")
    print(f"{'='*80}\n")
    
    img = Image.open(image_path)
    
    # Test different preprocessing combinations
    configs = [
        # (contrast, brightness, sharpness, threshold, psm, name)
        (2.0, 1.1, 2.0, 160, 6, "Default"),
        (2.5, 1.2, 2.5, 140, 6, "Enhanced + Low Threshold"),
        (3.0, 1.3, 3.0, 130, 6, "High Enhancement"),
        (2.0, 1.0, 2.0, 180, 6, "High Threshold"),
        (2.5, 1.2, 2.5, 160, 3, "PSM 3 (Auto)"),
        (2.5, 1.2, 2.5, 160, 4, "PSM 4 (Single Column)"),
        (2.0, 1.1, 2.0, 160, 11, "PSM 11 (Sparse Text)"),
        (1.5, 1.0, 1.5, 150, 6, "Light Processing"),
    ]
    
    for i, (contrast, brightness, sharpness, threshold, psm, name) in enumerate(configs, 1):
        print(f"\n--- Config {i}: {name} ---")
        print(f"Contrast: {contrast}, Brightness: {brightness}, Sharpness: {sharpness}")
        print(f"Threshold: {threshold}, PSM: {psm}")
        
        processed = preprocess_image(img, contrast, brightness, sharpness, threshold)
        
        # Save preprocessed image for visual inspection
        output_path = f"test_output_{i}_{name.replace(' ', '_')}.png"
        processed.save(output_path)
        print(f"Saved preprocessed image to: {output_path}")
        
        # Run OCR
        text = pytesseract.image_to_string(
            processed, 
            lang='spa+eng', 
            config=f'--psm {psm} --oem 3'
        )
        
        print("\nExtracted text:")
        print("-" * 40)
        print(text[:500] if len(text) > 500 else text)
        print("-" * 40)
        
        # Check for key data
        has_escuadron = 'escuadr' in text.lower() or 'squadron' in text.lower()
        has_percentages = '%' in text
        has_infanteria = 'infantería' in text.lower() or 'infanteria' in text.lower()
        has_ataque = 'ataque' in text.lower() or 'attack' in text.lower()
        
        print(f"\n✓ Detection results:")
        print(f"  Escuadrón/Squadron: {'✓' if has_escuadron else '✗'}")
        print(f"  Percentages: {'✓' if has_percentages else '✗'}")
        print(f"  Troop types: {'✓' if has_infanteria else '✗'}")
        print(f"  Attributes: {'✓' if has_ataque else '✗'}")
        
        score = sum([has_escuadron, has_percentages, has_infanteria, has_ataque])
        print(f"\n  Score: {score}/4")
        
        if score == 4:
            print(f"\n🎯 OPTIMAL CONFIG FOUND: {name}")
            return (contrast, brightness, sharpness, threshold, psm)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_config.py <image_path>")
        print("\nExample:")
        print("  python test_ocr_config.py data/example_top.png")
        print("  python test_ocr_config.py data/example_bottom.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    result = test_ocr_configs(image_path)
    
    if result:
        contrast, brightness, sharpness, threshold, psm = result
        print(f"\n{'='*80}")
        print("RECOMMENDED SETTINGS:")
        print(f"{'='*80}")
        print(f"Contrast: {contrast}")
        print(f"Brightness: {brightness}")
        print(f"Sharpness: {sharpness}")
        print(f"Threshold: {threshold}")
        print(f"PSM: {psm}")
        print("\nUpdate these values in utils/ocr_extractor.py")
