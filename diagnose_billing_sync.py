#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from billing_panel.clickup_client import ClickUpClient
from billing_panel.storage import BillingStorage

STATE_PATH = Path("/home/knycat/kingshot-bot/data/billing/panel_state.json")


def main() -> None:
    storage = BillingStorage(STATE_PATH)

    runs = storage.list_runs()
    print(f"runs_count={len(runs)}")
    if runs:
        print("latest_run_id=", runs[0].get("id"))
        print("latest_run_summary=", json.dumps(runs[0].get("summary", {}), ensure_ascii=False))

    mapping = storage.get_field_mapping()
    print("field_mapping=", json.dumps(mapping, ensure_ascii=False))

    token = storage.get_clickup_token()
    if not token:
        print("No ClickUp token in storage")
        return

    clickup = ClickUpClient(token=token)

    if not runs:
        print("No runs to inspect selection")
        return

    latest_selection = runs[0].get("selection", {})
    lists = latest_selection.get("lists", [])
    if not lists:
        print("Latest run has no list selection")
        return

    list_id = str(lists[0].get("list_id"))
    tasks = clickup.list_tasks(list_id)
    print(f"tasks_in_list={len(tasks)}")

    for task in tasks[:5]:
        task_id = str(task.get("id"))
        task_name = str(task.get("name", ""))
        status = str(task.get("status", {}).get("status", ""))
        print(f"\nTASK {task_id} | {task_name} | status={status}")
        custom_fields = task.get("custom_fields", []) or []
        if not custom_fields:
            print("  custom_fields: none")
            continue
        for cf in custom_fields:
            name = str(cf.get("name", ""))
            value = cf.get("value")
            print(f"  - {name} => {value!r}")


if __name__ == "__main__":
    main()
