from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .clickup_client import ClickUpClient
from .sheets_client import SheetsClient
from .storage import BillingStorage


class BillingSyncService:
    """Manual month-close sync service for ClickUp billing tasks."""

    DEFAULT_QUANTITY_FIELDS = ["cantidad", "quantity", "qty", "cant", "unidades"]
    DEFAULT_PRICE_FIELDS = [
        "precio por unidad",
        "precio unidad",
        "precio_unitario",
        "unit price",
        "price",
        "precio",
    ]

    def __init__(self, storage: BillingStorage, clickup: ClickUpClient | None, sheets: SheetsClient | None) -> None:
        self.storage = storage
        self.clickup = clickup
        self.sheets = sheets
        
        mapping = storage.get_field_mapping()
        mapped_quantity = self._read_csv(mapping.get("quantity_field_names", ""))
        mapped_price = self._read_csv(mapping.get("price_field_names", ""))
        self.quantity_fields = self._merge_candidates(mapped_quantity, self.DEFAULT_QUANTITY_FIELDS)
        self.price_fields = self._merge_candidates(mapped_price, self.DEFAULT_PRICE_FIELDS)
        self.required_status = (mapping.get("required_status_name", "terminada/facturada") or "").strip().lower()
        self.sheet_columns = self._read_csv(mapping.get("google_sheet_columns", "cantidad,descripcion,precio_unitario,total,clickup_task_id,cliente,mes,lista"))

    @staticmethod
    def _read_csv(csv_string: str) -> list[str]:
        if not csv_string:
            return []
        return [item.strip() for item in csv_string.split(",") if item.strip()]

    @staticmethod
    def _merge_candidates(primary: list[str], fallback: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for item in primary + fallback:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item.strip())
        return merged

    def run_sync(self, selection: dict[str, Any]) -> dict[str, Any]:
        if not self.clickup:
            raise RuntimeError("ClickUp token not configured.")
        if not self.sheets:
            raise RuntimeError("Google Sheets not configured.")

        run = self.storage.create_run(selection)
        items: list[dict[str, Any]] = []
        summary = {
            "spaces": len(selection.get("spaces", [])),
            "folders": len(selection.get("folders", [])),
            "lists": len(selection.get("lists", [])),
            "tasks_seen": 0,
            "tasks_synced": 0,
            "tasks_skipped": 0,
            "tasks_failed": 0,
        }

        for list_context in selection.get("lists", []):
            list_id = str(list_context["list_id"])
            list_name = list_context.get("list_name", list_id)
            folder_name = list_context.get("folder_name", "")
            space_name = list_context.get("space_name", "")
            
            # Get per-list configuration
            list_config = self.storage.get_list_config(list_id)
            if not list_config.get('spreadsheet_id') or not list_config.get('tab_name') or list_config.get('starting_row') is None:
                summary["tasks_skipped"] += 1
                items.append(
                    {
                        "task_id": list_id,
                        "task_name": list_name,
                        "list_name": list_name,
                        "status": "skipped",
                        "message": "Lista no configurada. Ve a 'Configurar Listas' para definir el documento Google Sheets.",
                    }
                )
                continue
            
            tasks = self.clickup.list_tasks(list_id)
            summary["tasks_seen"] += len(tasks)

            for task in tasks:
                task_id = str(task.get("id"))
                task_name = str(task.get("name", task_id))
                task_status = str(task.get("status", {}).get("status", "")).strip().lower()

                if self.required_status and task_status != self.required_status:
                    summary["tasks_skipped"] += 1
                    items.append(
                        {
                            "task_id": task_id,
                            "task_name": task_name,
                            "list_name": list_name,
                            "status": "skipped",
                            "message": f"Estado '{task_status}' no coincide con '{self.required_status}'",
                        }
                    )
                    continue

                quantity_raw = self.clickup.extract_custom_field(task, self.quantity_fields)
                unit_price_raw = self.clickup.extract_custom_field(task, self.price_fields)
                quantity = self.clickup.parse_decimal(quantity_raw)
                unit_price = self.clickup.parse_decimal(unit_price_raw)

                if quantity is None or unit_price is None:
                    summary["tasks_failed"] += 1
                    message = "Faltan campos obligatorios: cantidad o precio unitario."
                    items.append(
                        {
                            "task_id": task_id,
                            "task_name": task_name,
                            "list_name": list_name,
                            "status": "failed",
                            "message": message,
                        }
                    )
                    self.storage.set_task_result(
                        task_id,
                        {
                            "status": "failed",
                            "message": message,
                            "last_run_id": run["id"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    continue

                total = quantity * unit_price
                row_data = {
                    "cantidad": quantity,
                    "descripcion": task_name,
                    "precio_unitario": unit_price,
                }

                try:
                    # Use per-list configuration to write to specific spreadsheet and row
                    sheet_result = self.sheets.append_row_to_spreadsheet(
                        spreadsheet_id=list_config['spreadsheet_id'],
                        worksheet_name=list_config['tab_name'],
                        row_data=row_data,
                        starting_row=list_config['starting_row'],
                    )
                    summary["tasks_synced"] += 1
                    items.append(
                        {
                            "task_id": task_id,
                            "task_name": task_name,
                            "list_name": list_name,
                            "status": "synced",
                            "message": f"Sincronizada en {list_config['tab_name']} fila {list_config['starting_row']}",
                            "sheet_result": sheet_result,
                        }
                    )
                    self.storage.set_task_result(
                        task_id,
                        {
                            "status": "synced",
                            "message": f"Sincronizada en {list_config['tab_name']} fila {list_config['starting_row']}",
                            "last_run_id": run["id"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    # Increment starting row for next task in this list
                    list_config['starting_row'] += 1
                except Exception as exc:
                    summary["tasks_failed"] += 1
                    message = str(exc)
                    items.append(
                        {
                            "task_id": task_id,
                            "task_name": task_name,
                            "list_name": list_name,
                            "status": "failed",
                            "message": message,
                        }
                    )
                    self.storage.set_task_result(
                        task_id,
                        {
                            "status": "failed",
                            "message": message,
                            "last_run_id": run["id"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )

        self.storage.update_run(run["id"], "completed", summary, items)
        return self.storage.get_run(run["id"])
