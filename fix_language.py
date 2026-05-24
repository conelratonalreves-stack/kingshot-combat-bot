import json

# Fix the language settings
data = {
    "timezones": {
        "100002913253859328": "Europe/Madrid",
        "1437943273091239966": "America/New_York",
        "233963491852025858": "America/New_York"
    },
    "languages": {
        "100002913253859328": "en",
        "233963491852025858": "en"
    }
}

# Write it
with open("data/user_timezones.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✓ Language settings fixed!")
print(json.dumps(data, indent=2, ensure_ascii=False))
