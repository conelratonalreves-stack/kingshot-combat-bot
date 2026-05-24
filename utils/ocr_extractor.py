"""OCR extraction utilities for Kingshot battle reports."""

import re
import io
import os
import sys
from typing import Dict, Optional
import numpy as np

try:
    import pytesseract
    from PIL import Image, ImageEnhance
    
    # Configure Tesseract path for Windows
    if sys.platform == "win32":
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"[OCR] Tesseract configured: {path}")
                break
    
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def preprocess_image(image: Image.Image, contrast: float = 2.5, brightness: float = 1.2, 
                     sharpness: float = 2.5, threshold: int = 160) -> Image.Image:
    """Preprocess image for better OCR recognition with configurable parameters."""
    if not HAS_OCR:
        return image
    
    try:
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast/brightness/sharpness
        image = ImageEnhance.Contrast(image).enhance(contrast)
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Sharpness(image).enhance(sharpness)

        # Binarization to reduce noise
        arr = np.array(image)
        arr = np.where(arr > threshold, 255, 0).astype('uint8')
        image = Image.fromarray(arr)
        
        return image
    except Exception:
        return image


def extract_numbers_from_text(text: str) -> list:
    """Extract all numbers from text, handling thousands separators and negative signs.
    
    Handles formats like:
    - -9.900.000 (Spanish negative with dots as thousands separator)
    - -1,080,932 (English negative with commas as thousands separator)
    - 1.080.932 (Spanish positive: dots as thousands separator)
    - 1,080,932 (English positive: commas as thousands separator)
    - 1080932 (no separator)
    Returns: ['-9900000', '1080932'] preserving negative signs
    """
    # Find all number-like patterns with their positions
    # Pattern: optional negative, digits with optional separators
    pattern = r'-?\d+(?:[.,]\d{3})*(?:[.,]\d+)?'
    
    results = []
    seen_positions = set()  # Track which character positions we've already captured
    
    for match in re.finditer(pattern, text):
        start, end = match.span()
        
        # Skip if we've already captured a number overlapping this position
        if any(start <= pos < end for pos in seen_positions):
            continue
            
        match_text = match.group()
        has_negative = match_text.startswith('-')
        match_text = match_text.replace('-', '')
        
        # Determine format: if has dots in thousands positions, it's Spanish format
        # English: 150,000 or 1,080,932.50
        # Spanish: 150.000 or 1.080.932,50
        
        # Count dots and commas
        dot_count = match_text.count('.')
        comma_count = match_text.count(',')
        
        # If multiple dots or dots before last 3 digits, it's Spanish (dots as thousands)
        if dot_count > 1 or (dot_count == 1 and len(match_text.split('.')[-1]) == 3):
            # Spanish format: remove dots (thousands), convert comma to dot (decimal)
            cleaned = match_text.replace('.', '').replace(',', '.')
        else:
            # English format: remove commas (thousands), keep dot (decimal)
            cleaned = match_text.replace(',', '')
        
        try:
            float(cleaned)
            final_val = ('-' + cleaned) if has_negative else cleaned
            results.append(final_val)
            # Mark these positions as used
            for i in range(start, end):
                seen_positions.add(i)
        except ValueError:
            pass
    
    return results


def extract_battle_report_stats_with_retries(image_bytes: bytes, max_attempts: int = 3) -> Dict:
    """Try extracting stats with different OCR configurations.
    
    Attempts different preprocessing parameters to maximize extraction success.
    """
    # Different OCR configurations to try (contrast, brightness, sharpness, threshold, psm)
    configs = [
        {"contrast": 2.5, "brightness": 1.2, "sharpness": 2.5, "threshold": 160, "psm": 3, "name": "Auto Page Segmentation"},
        {"contrast": 2.5, "brightness": 1.2, "sharpness": 2.5, "threshold": 160, "psm": 4, "name": "Single Column"},
        {"contrast": 2.5, "brightness": 1.2, "sharpness": 2.5, "threshold": 160, "psm": 6, "name": "Default"},
        {"contrast": 3.0, "brightness": 1.3, "sharpness": 3.0, "threshold": 140, "psm": 3, "name": "High Enhancement Auto"},
        {"contrast": 2.0, "brightness": 1.0, "sharpness": 2.0, "threshold": 180, "psm": 4, "name": "High Threshold Column"},
        {"contrast": 1.8, "brightness": 1.1, "sharpness": 1.8, "threshold": 150, "psm": 6, "name": "Light Processing"},
        {"contrast": 3.5, "brightness": 1.4, "sharpness": 3.5, "threshold": 130, "psm": 11, "name": "Sparse Text PSM"},
    ]
    
    best_result = None
    best_score = -1
    
    for i, config in enumerate(configs[:max_attempts]):
        print(f"[OCR] Attempt {i+1}/{max_attempts} with config: {config['name']}")
        
        result = extract_battle_report_stats(
            image_bytes, 
            contrast=config["contrast"],
            brightness=config["brightness"],
            sharpness=config["sharpness"],
            threshold=config["threshold"],
            psm=config["psm"]
        )
        
        if result.get("success"):
            # Calculate quality score
            stats = result.get("stats", {})
            score = 0
            
            # Count non-zero attributes
            for side in stats.values():
                for troop in side.values():
                    score += sum(1 for attr in ['ataque', 'defensa', 'letalidad', 'salud'] 
                                if troop.get(attr) is not None and troop.get(attr) != 0.0)
                    if troop.get('count') is not None:
                        score += 2  # Counts are more valuable
            
            # Add points for squadron counts (but penalize unrealistic values)
            ally_t = result.get("ally_troops")
            enemy_t = result.get("enemy_troops")
            
            if ally_t and enemy_t:
                # Troop counts should be at least 1000 in real battles
                # If both are < 1000, likely reading wrong line
                if ally_t >= 1000 and enemy_t >= 1000:
                    score += 10  # Bonus for realistic troop counts
                elif ally_t < 100 or enemy_t < 100:
                    score -= 20  # Heavy penalty for unrealistic counts
                else:
                    score += 5  # Some points for any detection
            elif ally_t or enemy_t:
                score += 2  # Minimal points if only one detected
            
            print(f"[OCR] Config '{config['name']}' score: {score}")
            
            if score > best_score:
                best_score = score
                best_result = result
                best_result["ocr_config"] = config["name"]
            
            # If we got a perfect score, stop trying
            if score >= 30:  # 12 attributes + 6 counts + 2 squadron = 32 max
                print(f"[OCR] Excellent extraction with '{config['name']}', stopping early")
                break
        else:
            print(f"[OCR] Config '{config['name']}' failed: {result.get('error')}")
    
    if best_result:
        print(f"[OCR] Best result from config: {best_result.get('ocr_config')} (score: {best_score})")
        return best_result
    else:
        return {
            "success": False,
            "error": f"Failed to extract data after {max_attempts} attempts with different OCR configurations"
        }


def extract_battle_report_stats(image_bytes: bytes, contrast: float = 2.5, brightness: float = 1.2,
                               sharpness: float = 2.5, threshold: int = 160, psm: int = 6) -> Dict:
    """Extract battle stats from a single screenshot with configurable OCR parameters.

    TOP image: Squadron/Squad line (total troops) - LANGUAGE INDEPENDENT
        Pattern: "NUMBER word NUMBER" where both numbers are large (>1000)
        Left number = allies, Right number = enemies
    BOTTOM image: 
    - Troop counts per type (Infantry/Cavalry/Archers) to calculate percentages
    - Attribute bonuses (Attack/Defense/Lethality/Health) for each troop type
    """
    if not HAS_OCR:
        return {
            "success": False,
            "error": "OCR not available. Install pytesseract and tesseract-ocr"
        }
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Get image dimensions
        width, height = img.size
        
        # Do a quick OCR test to determine if this is TOP or BOTTOM image
        # TOP image: Has "Squad/Escuadrón" line with troop counts
        # BOTTOM image: Has MANY percentages (equipment stats) without Squad keyword
        test_crop = img.crop((0, int(height * 0.2), width, int(height * 0.8)))
        test_text = pytesseract.image_to_string(test_crop, lang='spa+eng', config='--psm 3 --oem 3')
        test_text_lower = test_text.lower()
        
        # Squad keywords (same as used for line detection)
        squad_keywords = ['squad', 'escuad', 'escad', 'schwad', 'staff', 'szwad', 'skuad', 'pasuk', 'filo', 'tak', 'phi']
        
        # Check if any squad keyword is present
        has_squad = any(keyword in test_text_lower for keyword in squad_keywords)
        
        # Determine image type
        if has_squad:
            # Has Squad keyword → definitely TOP image
            is_bottom_image = False
        else:
            # No Squad keyword → check if it has many % (BOTTOM has 20+ percentages)
            is_bottom_image = test_text.count('%') > 10
        
        print(f"[DEBUG] Image detection: is_bottom={is_bottom_image}, has_squad={has_squad}, percent_count={test_text.count('%')}")
        
        if not is_bottom_image:
            # This is TOP image - read full image and find Squad line by keywords
            # Use full image to detect Squad line in multiple languages
            img_to_process = img
            actual_psm = 6  # Block of text mode to read all lines
            print(f"[DEBUG] TOP image detected, reading full image to find Squad line")
        else:
            # This is BOTTOM image - use full image (NO CROP)
            img_to_process = img
            actual_psm = psm  # Use provided PSM (default 6)
        
        # Preprocess with custom parameters
        processed = preprocess_image(img_to_process, contrast, brightness, sharpness, threshold)
        
        # Extract text with appropriate PSM
        text = pytesseract.image_to_string(processed, lang='spa+eng', config=f'--psm {actual_psm} --oem 3')
        
        # Initialize stats structure
        stats = {
            'aliados': {
                'infanteria': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None},
                'caballeria': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None},
                'arquero': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None}
            },
            'enemigos': {
                'infanteria': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None},
                'caballeria': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None},
                'arquero': {'ataque': None, 'defensa': None, 'letalidad': None, 'salud': None, 'count': None}
            }
        }

        # Total troop counts from Escuadrón/Squadron field (TOP image)
        ally_troops = None
        enemy_troops = None
        
        def parse_lines(lines_text: str):
            nonlocal ally_troops, enemy_troops
            current_type_local = None
            troop_counts_found = False
            
            for line in lines_text.split('\n'):
                line_lower = line.lower().strip()
                if not line_lower:
                    continue

                # Extract total troop count from Squad line (TOP image)
                # Search for Squad line by flexible keywords that work across languages
                if ally_troops is None and '%' not in line:
                    # Short, flexible keywords that capture variations in all languages
                    # Using partial matches to be more flexible with OCR errors and variations
                    squad_keywords = [
                        'squad',      # English: squad, squadron
                        'escuad',     # Spanish/Portuguese: escuadrón, esquadrão
                        'escad',      # French: escadron, escadron
                        'schwad',     # German: schwadron
                        'staff',      # German: staffel
                        'szwad',      # Polish: szwadron
                        'skuad',      # Indonesian: skuadron
                        'pasuk',      # Indonesian: pasukan
                        'filo',       # Turkish: filo
                        'tak',        # Turkish: takım
                        'phi',        # Vietnamese: phi đội
                        # These short patterns will match variations and OCR errors
                    ]
                    
                    line_lower = line.lower()
                    is_squad_line = any(keyword in line_lower for keyword in squad_keywords)
                    
                    if is_squad_line:
                        print(f"[DEBUG OCR] Squad line found: '{line}'")
                        nums = extract_numbers_from_text(line)
                        print(f"[DEBUG OCR] Numbers extracted: {nums}")
                        # Filter only positive numbers that look like real troop counts
                        positive_nums = []
                        for n in nums:
                            try:
                                num_val = int(float(n))
                                # Only positive numbers >= 1000 (realistic troop counts)
                                if num_val >= 1000:
                                    positive_nums.append(num_val)
                            except (ValueError, TypeError):
                                continue
                        
                        print(f"[DEBUG OCR] Filtered numbers (>=1000): {positive_nums}")
                        
                        if len(positive_nums) >= 2:
                            # Format: "ally_number  Squad  enemy_number"
                            # Left number = ally (first), Right number = enemy (second)
                            ally_troops = positive_nums[0]  # First number (left side)
                            enemy_troops = positive_nums[1]  # Second number (right side)
                            print(f"[DEBUG OCR] Assigned from Squad line: ally={ally_troops}, enemy={enemy_troops}")

                # Try to extract composition data from BOTTOM image (6 numbers in one line)
                if not is_bottom_image:
                    nums = extract_numbers_from_text(line)
                    if len(nums) == 6:
                        try:
                            ally_inf = int(float(nums[0]))
                            ally_cav = int(float(nums[1]))
                            ally_arc = int(float(nums[2]))
                            enemy_inf = int(float(nums[3]))
                            enemy_cav = int(float(nums[4]))
                            enemy_arc = int(float(nums[5]))
                            
                            # Validate they're reasonable troop counts
                            if all(0 < c < 10000000 for c in [ally_inf, ally_cav, ally_arc, enemy_inf, enemy_cav, enemy_arc]):
                                stats['aliados']['infanteria']['count'] = ally_inf
                                stats['aliados']['caballeria']['count'] = ally_cav
                                stats['aliados']['arquero']['count'] = ally_arc
                                stats['enemigos']['infanteria']['count'] = enemy_inf
                                stats['enemigos']['caballeria']['count'] = enemy_cav
                                stats['enemigos']['arquero']['count'] = enemy_arc
                                troop_counts_found = True
                        except (ValueError, IndexError):
                            pass

                # Troop type detection (BOTTOM image)
                if 'infantería' in line_lower or 'infanteria' in line_lower or 'infantry' in line_lower:
                    current_type_local = 'infanteria'
                elif 'caballería' in line_lower or 'caballeria' in line_lower or 'cavalry' in line_lower:
                    current_type_local = 'caballeria'
                elif 'arquero' in line_lower or 'archer' in line_lower:
                    current_type_local = 'arquero'

                # Extract attribute percentages - improved to handle two-digit percentages
                if current_type_local:
                    # More flexible pattern to catch percentages like +21.0%, +14.0%, +117.8%, etc.
                    percentages = re.findall(r'([+-]?\d+(?:[,.]?\d+)?)%', line)
                    if len(percentages) >= 2:
                        try:
                            # Clean and convert to float
                            allied_val = float(percentages[0].replace(',', '.').replace('+', ''))
                            enemy_val = float(percentages[1].replace(',', '.').replace('+', ''))
                            
                            # Detect attribute type from line
                            if 'ataque' in line_lower or 'attack' in line_lower:
                                stats['aliados'][current_type_local]['ataque'] = stats['aliados'][current_type_local]['ataque'] or allied_val
                                stats['enemigos'][current_type_local]['ataque'] = stats['enemigos'][current_type_local]['ataque'] or enemy_val
                            elif 'defensa' in line_lower or 'defense' in line_lower:
                                stats['aliados'][current_type_local]['defensa'] = stats['aliados'][current_type_local]['defensa'] or allied_val
                                stats['enemigos'][current_type_local]['defensa'] = stats['enemigos'][current_type_local]['defensa'] or enemy_val
                            elif 'letalidad' in line_lower or 'lethality' in line_lower:
                                stats['aliados'][current_type_local]['letalidad'] = stats['aliados'][current_type_local]['letalidad'] or allied_val
                                stats['enemigos'][current_type_local]['letalidad'] = stats['enemigos'][current_type_local]['letalidad'] or enemy_val
                            elif 'salud' in line_lower or 'health' in line_lower:
                                stats['aliados'][current_type_local]['salud'] = stats['aliados'][current_type_local]['salud'] or allied_val
                                stats['enemigos'][current_type_local]['salud'] = stats['enemigos'][current_type_local]['salud'] or enemy_val
                        except (ValueError, IndexError) as e:
                            print(f"[OCR] Failed to parse percentages from line: {line}, error: {e}")
                            pass

        parse_lines(text)

        # If we still lack attribute stats, try OCR on different sections
        has_attr_allied = any(
            any(troop[attr] is not None for attr in ('ataque','defensa','letalidad','salud'))
            for troop in stats['aliados'].values()
        )
        has_attr_enemy = any(
            any(troop[attr] is not None for attr in ('ataque','defensa','letalidad','salud'))
            for troop in stats['enemigos'].values()
        )

        if not (has_attr_allied and has_attr_enemy):
            try:
                width, height = img.size
                # Try right half
                right = img.crop((width//2, 0, width, height))
                right_proc = preprocess_image(right, contrast, brightness, sharpness, max(threshold - 20, 120))
                right_text = pytesseract.image_to_string(right_proc, lang='spa+eng', config=f'--psm {psm} --oem 3')
                parse_lines(right_text)
            except Exception:
                pass
        
        # If still no attributes, try bottom half
        has_attr_allied = any(
            any(troop[attr] is not None for attr in ('ataque','defensa','letalidad','salud'))
            for troop in stats['aliados'].values()
        )
        has_attr_enemy = any(
            any(troop[attr] is not None for attr in ('ataque','defensa','letalidad','salud'))
            for troop in stats['enemigos'].values()
        )
        
        if not (has_attr_allied and has_attr_enemy):
            try:
                width, height = img.size
                bottom = img.crop((0, height//2, width, height))
                bottom_proc = preprocess_image(bottom, contrast, brightness, sharpness, max(threshold - 10, 130))
                bottom_text = pytesseract.image_to_string(bottom_proc, lang='spa+eng', config=f'--psm {psm} --oem 3')
                parse_lines(bottom_text)
            except Exception:
                pass
        
        # Check what data we extracted
        has_squadron_counts = ally_troops is not None or enemy_troops is not None
        
        # Check if we have meaningful attribute data (non-zero percentages)
        has_attributes = any(
            any(troop.get(attr) is not None and troop.get(attr) != 0.0 
                for attr in ['ataque', 'defensa', 'letalidad', 'salud'])
            for side in stats.values()
            for troop in side.values()
        )
        
        # Check if we have troop type counts
        has_troop_counts = any(
            troop.get('count') is not None
            for side in stats.values()
            for troop in side.values()
        )
        
        # Apply default values for missing attributes only if we didn't extract any
        if not has_attributes:
            for side in ['aliados', 'enemigos']:
                for troop_type in stats[side]:
                    for attr in ['ataque', 'defensa', 'letalidad', 'salud']:
                        if stats[side][troop_type][attr] is None:
                            stats[side][troop_type][attr] = 0.0
        
        # Success if we have squadron counts (TOP) OR attributes (BOTTOM) OR troop counts (BOTTOM)
        if has_squadron_counts or has_attributes or has_troop_counts:
            print(f"[OCR] Success - ally_troops: {ally_troops}, enemy_troops: {enemy_troops}")
            return {
                "success": True,
                "stats": stats,
                "raw_text": text,
                "ally_troops": ally_troops,
                "enemy_troops": enemy_troops
            }
        else:
            print(f"[OCR] Failed - no valid data found")
            return {
                "success": False,
                "error": "Could not extract complete stats from image. Make sure both allied and enemy stats are visible.",
                "partial_stats": stats,
                "raw_text": text
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error processing image: {str(e)}"
        }


def parse_troop_input(input_string: str) -> dict:
    """Parse total troops input from string.
    
    Accepts: "900450" or "1080000"
    """
    try:
        # Extract numbers only
        numbers = extract_numbers_from_text(input_string)
        
        if numbers:
            total_troops = int(numbers[0])
            if total_troops <= 0:
                return {
                    "success": False,
                    "error": "Troop count must be greater than 0"
                }
            
            return {
                "success": True,
                "total_troops": total_troops
            }
        
        return {
            "success": False,
            "error": "Could not parse troop number. Use format: 900450"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing troops: {str(e)}"
        }
