#!/usr/bin/env python3
import json
from pathlib import Path

storage_path = Path("/home/knycat/kingshot-bot/data/billing/panel_state.json")

with open(storage_path, "r") as f:
    data = json.load(f)

url = data["credentials"]["google_sheets_spreadsheet_id"]
if url and "docs.google.com" in url:
    id_part = url.split("/d/")[1].split("/")[0]
    data["credentials"]["google_sheets_spreadsheet_id"] = id_part
    
    with open(storage_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Corrected ID: {id_part}")
else:
    print("✓ ID already valid or not configured")
