from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class BillingStorage:
    """JSON storage for billing panel state and sync results."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state = self._load_json(
            state_file,
            {
                "preferences": {
                    "last_team_id": None,
                    "last_selected_space_ids": [],
                    "last_selected_folder_ids": [],
                    "last_selected_list_ids": [],
                },
                "processed_tasks": {},
                "runs": [],
            },
        )
        self._normalize()

    def _load_json(self, path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return fallback
        try:
            with path.open("r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except Exception:
            return fallback

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)
        temp_path.replace(self.state_file)

    def _normalize(self) -> None:
        self.state.setdefault("preferences", {})
        self.state["preferences"].setdefault("last_team_id", None)
        self.state["preferences"].setdefault("last_selected_space_ids", [])
        self.state["preferences"].setdefault("last_selected_folder_ids", [])
        self.state["preferences"].setdefault("last_selected_list_ids", [])
        self.state.setdefault("credentials", {})
        self.state["credentials"].setdefault("clickup_token", None)
        self.state["credentials"].setdefault("clickup_team_id", None)
        self.state["credentials"].setdefault("google_sheets_spreadsheet_id", None)
        self.state["credentials"].setdefault("google_sheets_tab_name", None)
        self.state.setdefault("field_mapping", {})
        self.state["field_mapping"].setdefault("quantity_field_names", "cantidad,quantity,qty")
        self.state["field_mapping"].setdefault("price_field_names", "precio por unidad,precio_unitario,unit price,price,precio")
        self.state["field_mapping"].setdefault("google_sheet_columns", "cantidad,descripcion,precio_unitario,total,clickup_task_id,cliente,mes,lista")
        self.state["field_mapping"].setdefault("required_status_name", "terminada/facturada")
        self.state.setdefault("list_configs", {})  # Per-list Google Sheets configuration
        self.state.setdefault("hierarchy_cache", {})
        self.state.setdefault("processed_tasks", {})
        self.state.setdefault("runs", [])

    def save(self) -> None:
        self._atomic_write(self.state)

    def remember_selection(self, team_id: str | None, space_ids: list[str], folder_ids: list[str], list_ids: list[str]) -> None:
        self.state["preferences"]["last_team_id"] = team_id
        self.state["preferences"]["last_selected_space_ids"] = space_ids
        self.state["preferences"]["last_selected_folder_ids"] = folder_ids
        self.state["preferences"]["last_selected_list_ids"] = list_ids
        self.save()

    def create_run(self, selection: dict[str, Any]) -> dict[str, Any]:
        run = {
            "id": str(uuid4()),
            "status": "running",
            "created_at": selection.get("created_at"),
            "selection": selection,
            "summary": {
                "spaces": 0,
                "folders": 0,
                "lists": 0,
                "tasks_seen": 0,
                "tasks_synced": 0,
                "tasks_skipped": 0,
                "tasks_failed": 0,
            },
            "items": [],
        }
        self.state["runs"].insert(0, run)
        self.state["runs"] = self.state["runs"][:20]
        self.save()
        return run

    def update_run(self, run_id: str, status: str, summary: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
        for run in self.state["runs"]:
            if run["id"] == run_id:
                run["status"] = status
                run["summary"] = summary
                run["items"] = items
                break
        self.save()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        for run in self.state.get("runs", []):
            if run["id"] == run_id:
                return run
        return None

    def latest_run(self) -> dict[str, Any] | None:
        runs = self.state.get("runs", [])
        return runs[0] if runs else None

    def list_runs(self) -> list[dict[str, Any]]:
        return list(self.state.get("runs", []))

    def task_was_synced(self, task_id: str) -> bool:
        record = self.state["processed_tasks"].get(str(task_id))
        return bool(record and record.get("status") == "synced")

    def set_task_result(self, task_id: str, payload: dict[str, Any]) -> None:
        self.state["processed_tasks"][str(task_id)] = payload
        self.save()

    def set_clickup_token(self, token: str | None) -> None:
        self.state["credentials"]["clickup_token"] = token
        self.save()

    def get_clickup_token(self) -> str | None:
        return self.state["credentials"].get("clickup_token")

    def set_clickup_team_id(self, team_id: str | None) -> None:
        self.state["credentials"]["clickup_team_id"] = team_id
        self.save()

    def get_clickup_team_id(self) -> str | None:
        return self.state["credentials"].get("clickup_team_id")

    def set_google_sheets_spreadsheet_id(self, spreadsheet_id: str | None) -> None:
        if spreadsheet_id:
            # Extract ID from URL if user pasted the full URL
            if "docs.google.com/spreadsheets" in spreadsheet_id:
                # URL format: https://docs.google.com/spreadsheets/d/ID/...
                parts = spreadsheet_id.split("/d/")
                if len(parts) > 1:
                    id_part = parts[1].split("/")[0]
                    spreadsheet_id = id_part
            self.state["credentials"]["google_sheets_spreadsheet_id"] = spreadsheet_id.strip()
        else:
            self.state["credentials"]["google_sheets_spreadsheet_id"] = None
        self.save()

    def get_google_sheets_spreadsheet_id(self) -> str | None:
        return self.state["credentials"].get("google_sheets_spreadsheet_id")

    def set_google_sheets_tab_name(self, tab_name: str | None) -> None:
        self.state["credentials"]["google_sheets_tab_name"] = tab_name or "Hoja1"
        self.save()

    def get_google_sheets_tab_name(self) -> str | None:
        return self.state["credentials"].get("google_sheets_tab_name", "Hoja1")

    def set_field_mapping(self, quantity_names: str, price_names: str, sheet_columns: str, required_status: str) -> None:
        self.state["field_mapping"]["quantity_field_names"] = quantity_names
        self.state["field_mapping"]["price_field_names"] = price_names
        self.state["field_mapping"]["google_sheet_columns"] = sheet_columns
        self.state["field_mapping"]["required_status_name"] = required_status
        self.save()

    def get_field_mapping(self) -> dict[str, str]:
        return self.state.get("field_mapping", {
            "quantity_field_names": "cantidad,quantity,qty",
            "price_field_names": "precio por unidad,precio_unitario,unit price,price,precio",
            "google_sheet_columns": "cantidad,descripcion,precio_unitario,total,clickup_task_id,cliente,mes,lista",
            "required_status_name": "terminada/facturada"
        })

    def set_list_config(self, list_id: str, spreadsheet_id: str | None, tab_name: str | None, starting_row: int | None) -> None:
        """Store per-list Google Sheets configuration."""
        list_id = str(list_id)
        if not self.state["list_configs"].get(list_id):
            self.state["list_configs"][list_id] = {}
        
        if spreadsheet_id:
            # Extract ID from URL if user pasted the full URL
            if "docs.google.com/spreadsheets" in spreadsheet_id:
                parts = spreadsheet_id.split("/d/")
                if len(parts) > 1:
                    id_part = parts[1].split("/")[0]
                    spreadsheet_id = id_part
            self.state["list_configs"][list_id]["spreadsheet_id"] = spreadsheet_id.strip()
        
        if tab_name:
            self.state["list_configs"][list_id]["tab_name"] = tab_name.strip()
        
        if starting_row is not None:
            self.state["list_configs"][list_id]["starting_row"] = int(starting_row)
        
        self.save()

    def get_list_config(self, list_id: str) -> dict[str, Any]:
        """Get per-list Google Sheets configuration."""
        list_id = str(list_id)
        return self.state.get("list_configs", {}).get(list_id, {})

    def get_all_list_configs(self) -> dict[str, Any]:
        """Get all list configurations."""
        return self.state.get("list_configs", {})

    def set_hierarchy_cache(self, team_id: str | None, hierarchy: dict[str, Any]) -> None:
        """Store latest ClickUp hierarchy for dashboard rendering without API calls."""
        cache_key = str(team_id or "default")
        self.state.setdefault("hierarchy_cache", {})
        self.state["hierarchy_cache"][cache_key] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "hierarchy": hierarchy,
        }
        self.save()

    def get_hierarchy_cache(self, team_id: str | None) -> dict[str, Any] | None:
        """Get cached hierarchy for a team."""
        cache_key = str(team_id or "default")
        return self.state.get("hierarchy_cache", {}).get(cache_key)
