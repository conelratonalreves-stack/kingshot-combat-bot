#!/usr/bin/env python3
import json

with open("/home/knycat/kingshot-bot/data/billing/panel_state.json", "r") as f:
    data = json.load(f)
    if data.get("runs"):
        latest = data["runs"][-1]
        print(json.dumps(latest, indent=2, ensure_ascii=False))
    else:
        print("No runs recorded")
