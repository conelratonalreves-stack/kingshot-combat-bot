"""
OCR extractor for player profile screenshots.
Extracts: player name, ID, alliance, power, kills, kingdom
"""

import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import io
import re
from typing import Dict, Optional, Tuple


def _preprocess_image(image_bytes: bytes) -> Image.Image:
    """Light preprocessing to improve OCR on profile screenshots."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Upscale to help OCR on small mobile screenshots
    upscale_factor = 2
    new_size = (img.width * upscale_factor, img.height * upscale_factor)
    img = img.resize(new_size, Image.LANCZOS)
    # Boost contrast slightly and convert to grayscale
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    return img


def _ocr_full_text(img: Image.Image) -> str:
    """Run general OCR across multiple languages."""
    return pytesseract.image_to_string(
        img,
        lang='eng+spa+fra',
        config='--psm 6 --oem 3'
    )


def _ocr_digits(img: Image.Image) -> str:
    """Run a digits-only OCR pass to improve ID extraction."""
    return pytesseract.image_to_string(
        img,
        lang='eng',
        config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'
    )


def _best_match(pattern: str, text: str) -> Optional[re.Match]:
    """Return first regex match helper."""
    return re.search(pattern, text, re.IGNORECASE)


def extract_player_profile(image_bytes: bytes) -> Dict:
    """
    Extract player profile data from screenshot.
    
    Returns dict with:
    - success: bool
    - name: str (player name)
    - player_id: str (numeric ID)
    - alliance: str (alliance tag, 2-4 letters)
    - power: str (e.g., "11,7M")
    - kills: str (e.g., "510 604")
    - kingdom: str (e.g., "#757")
    - error: str (if success=False)
    """
    try:
        img = _preprocess_image(image_bytes)

        # OCR passes
        text = _ocr_full_text(img)
        digits_text = _ocr_digits(img)

        print(f"[DEBUG OCR Profile] Full text:\n{text}")
        print(f"[DEBUG OCR Profile] Digits text:\n{digits_text}")

        # Extract alliance + name when they are on the same line like: [TAG]NAME
        name = None
        alliance = None
        for line in text.split('\n'):
            line_clean = line.strip()
            if not line_clean:
                continue
            # Pattern [TAG]Name
            bracket_match = re.search(r'\[([A-Za-z0-9]{2,4})\]\s*([A-Za-z0-9 .\'"-]{2,32})', line_clean)
            if bracket_match:
                alliance = bracket_match.group(1).upper()
                name = bracket_match.group(2).strip()
                break
        # If not found, fall back to first non-label line with letters
        if name is None:
            for line in text.split('\n'):
                line_clean = line.strip()
                if not line_clean:
                    continue
                # Skip obvious labels/titles (perfil/profile/governor/kingdom/id/alliance)
                if re.search(r'ID|Alliance|Alianza|Kingdom|Reino|Perfil|Profile|Gobernador|Governor', line_clean, re.IGNORECASE):
                    continue
                if re.search(r'[A-Za-z]', line_clean) and len(line_clean) > 3:
                    name = line_clean
                    break

        # Extract ID: prefer digits-only OCR, fallback to full text, then any 7-12 digit run
        player_id = None
        id_match_digits = _best_match(r'(\d{8,10})', digits_text)
        if id_match_digits:
            player_id = id_match_digits.group(1)
        else:
            id_match_text = _best_match(r'ID[^0-9]{0,4}(\d{7,12})', text)
            if id_match_text:
                player_id = id_match_text.group(1)
            else:
                # Fallback: take the longest 7-12 digit sequence found anywhere
                candidates = re.findall(r'\d{7,12}', digits_text + " " + text)
                if candidates:
                    player_id = max(candidates, key=len)

        # Extract Alliance (after keyword), allow 2-4 alnum, unless already from bracket
        if alliance is None:
            alliance_match = _best_match(r'Alliance\s*:?[\s#-]*([A-Z0-9]{2,4})', text)
            if alliance_match:
                alliance = alliance_match.group(1).upper()
            else:
                token_match = _best_match(r'\b([A-Z]{3,4})\b', text)
                if token_match:
                    alliance = token_match.group(1)

        # Extract Power (number with M, K, or B suffix)
        power = None
        power_match = _best_match(r'([\d,.]+\s*[KMB])', text)
        if power_match:
            power = power_match.group(1).replace(' ', '')

        # Extract Kills
        kills = None
        kills_match = _best_match(r'(?:Tu\u00e9s|Kills|Asesinatos)\s*:?[\s#-]*([\d\s,.]+)', text)
        if kills_match:
            kills = kills_match.group(1).strip()

        # Extract Kingdom
        kingdom = None
        kingdom_match = _best_match(r'(?:Royaume|Kingdom|Reino)\s*:?[\s#-]*(#?\d+)', text)
        if kingdom_match:
            kingdom = kingdom_match.group(1)
            if not kingdom.startswith('#'):
                kingdom = '#' + kingdom

        # Validation: at least name and ID are required
        if not name or not player_id:
            return {
                'success': False,
                'error': f'Could not extract required data. Found: name={name}, id={player_id}'
            }

        return {
            'success': True,
            'name': name,
            'player_id': player_id,
            'alliance': alliance,
            'power': power,
            'kills': kills,
            'kingdom': kingdom
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'OCR extraction failed: {str(e)}'
        }


def format_profile_data(data: Dict) -> str:
    """Format extracted profile data for display."""
    if not data.get('success'):
        return f"❌ {data.get('error', 'Unknown error')}"
    
    lines = [
        f"📋 **Extracted Data:**",
        f"👤 **Name:** {data['name']}",
        f"🆔 **ID:** {data['player_id']}"
    ]
    
    if data.get('alliance'):
        lines.append(f"🛡️ **Alliance:** {data['alliance']}")
    if data.get('power'):
        lines.append(f"⚡ **Power:** {data['power']}")
    if data.get('kills'):
        lines.append(f"⚔️ **Kills:** {data['kills']}")
    if data.get('kingdom'):
        lines.append(f"🏰 **Kingdom:** {data['kingdom']}")
    
    return '\n'.join(lines)
