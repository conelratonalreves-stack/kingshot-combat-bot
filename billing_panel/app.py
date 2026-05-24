from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from .clickup_client import ClickUpClient
from .sheets_client import SheetsClient
from .storage import BillingStorage
from .sync_service import BillingSyncService


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "billing"
STATE_FILE = DATA_DIR / "panel_state.json"


def create_app() -> Flask:
    template_dir = str(BASE_DIR / "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.getenv("BILLING_PANEL_SECRET", "billing-panel-dev-secret")

    storage = BillingStorage(STATE_FILE)

    def build_clients() -> tuple[ClickUpClient | None, SheetsClient | None, list[str]]:
        warnings: list[str] = []
        token = storage.get_clickup_token() or os.getenv("CLICKUP_API_TOKEN")
        if token:
            clickup = ClickUpClient(token=token)
        else:
            clickup = None
            warnings.append("No se encontró token de ClickUp. Configúralo en Ajustes.")
        sheets = None
        try:
            sheets = SheetsClient.from_env()
        except Exception as exc:
            warnings.append(str(exc))
        return clickup, sheets, warnings

    @app.get("/")
    def dashboard():
        clickup, sheets, warnings = build_clients()
        team_id = os.getenv("CLICKUP_TEAM_ID") or storage.state["preferences"].get("last_team_id")
        hierarchy = {"team_id": team_id, "spaces": []}
        cache_updated_at = None
        hierarchy_error = None
        hierarchy_cache = storage.get_hierarchy_cache(team_id)
        if hierarchy_cache:
            hierarchy = hierarchy_cache.get("hierarchy", hierarchy)
            cache_updated_at = hierarchy_cache.get("updated_at")
        else:
            warnings.append("La jerarquía está en caché local. Pulsa 'Refrescar jerarquía' para consultar ClickUp.")

        last_run = storage.latest_run()
        runs = storage.list_runs()
        list_configs = storage.get_all_list_configs()
        return render_template(
            "billing_panel.html",
            hierarchy=hierarchy,
            last_run=last_run,
            runs=runs,
            warnings=warnings,
            hierarchy_error=hierarchy_error,
            preferences=storage.state["preferences"],
            panel_ready=bool(clickup and sheets),
            list_configs=list_configs,
            cache_updated_at=cache_updated_at,
        )

    @app.post("/refresh-hierarchy")
    def refresh_hierarchy():
        clickup, _, _ = build_clients()
        if not clickup:
            flash("No se puede refrescar: falta token de ClickUp.", "error")
            return redirect(url_for("dashboard"))

        team_id = os.getenv("CLICKUP_TEAM_ID") or storage.state["preferences"].get("last_team_id")
        try:
            hierarchy = clickup.discover_hierarchy(team_id)
            storage.set_hierarchy_cache(hierarchy.get("team_id") or team_id, hierarchy)
            flash("Jerarquía actualizada desde ClickUp.", "success")
        except Exception as exc:
            flash(f"Error al refrescar jerarquía: {exc}", "error")
        return redirect(url_for("dashboard"))

    @app.post("/sync")
    def sync_month_close():
        clickup, sheets, warnings = build_clients()
        if not clickup or not sheets:
            flash("Faltan credenciales para ClickUp o Google Sheets.", "error")
            return redirect(url_for("dashboard"))

        selected_list_ids = request.form.getlist("list_id")
        selected_space_ids = request.form.getlist("space_id")
        selected_folder_ids = request.form.getlist("folder_id")

        if selected_folder_ids and selected_list_ids:
            # Defensive guard in case client sends a mixed selection.
            selected_list_ids = []
            flash("Selección mixta detectada: se sincronizarán solo carpetas para evitar duplicados.", "warning")

        if not selected_list_ids and not selected_space_ids and not selected_folder_ids:
            flash("Selecciona al menos un cliente o una carpeta de mes para sincronizar.", "error")
            return redirect(url_for("dashboard"))

        try:
            team_id = os.getenv("CLICKUP_TEAM_ID") or storage.state["preferences"].get("last_team_id")
            hierarchy_cache = storage.get_hierarchy_cache(team_id)
            hierarchy = hierarchy_cache.get("hierarchy", {"team_id": team_id, "spaces": []}) if hierarchy_cache else {"team_id": team_id, "spaces": []}
            selected_selection = build_selection_payload(hierarchy, selected_space_ids, selected_folder_ids, selected_list_ids)
            if not selected_selection.get("lists") and selected_list_ids:
                selected_selection["lists"] = [
                    {
                        "space_id": "",
                        "space_name": "",
                        "folder_id": "",
                        "folder_name": "",
                        "list_id": str(list_id),
                        "list_name": str(list_id),
                    }
                    for list_id in selected_list_ids
                ]
            storage.remember_selection(
                hierarchy.get("team_id"),
                selected_space_ids,
                selected_folder_ids,
                selected_list_ids,
            )
            service = BillingSyncService(storage, clickup, sheets)
            run = service.run_sync({**selected_selection, "created_at": datetime.now(timezone.utc).isoformat()})
            flash(
                f"Sincronización completada: {run['summary']['tasks_synced']} sincronizadas, {run['summary']['tasks_failed']} fallidas, {run['summary']['tasks_skipped']} omitidas.",
                "success",
            )
            return redirect(url_for("dashboard"))
        except Exception as exc:
            flash(f"Error al sincronizar: {exc}", "error")
            return redirect(url_for("dashboard"))

    @app.get("/runs/<run_id>")
    def run_detail(run_id: str):
        run = storage.get_run(run_id)
        if not run:
            flash("No se encontró la ejecución solicitada.", "error")
            return redirect(url_for("dashboard"))

        clickup, sheets, warnings = build_clients()
        team_id = os.getenv("CLICKUP_TEAM_ID") or storage.state["preferences"].get("last_team_id")
        hierarchy = {"team_id": team_id, "spaces": []}
        cache_updated_at = None
        hierarchy_cache = storage.get_hierarchy_cache(team_id)
        if hierarchy_cache:
            hierarchy = hierarchy_cache.get("hierarchy", hierarchy)
            cache_updated_at = hierarchy_cache.get("updated_at")

        return render_template(
            "billing_panel.html",
            hierarchy=hierarchy,
            last_run=run,
            runs=storage.list_runs(),
            warnings=warnings,
            hierarchy_error=None,
            preferences=storage.state["preferences"],
            panel_ready=bool(clickup and sheets),
            list_configs=storage.get_all_list_configs(),
            cache_updated_at=cache_updated_at,
        )

    @app.get("/settings")
    def settings_page():
        mapping = storage.get_field_mapping()
        return render_template(
            "settings.html",
            clickup_token=storage.get_clickup_token(),
            clickup_token_masked=("*" * (len(storage.get_clickup_token()) - 4) + storage.get_clickup_token()[-4:]) if storage.get_clickup_token() else None,
            quantity_field_names=mapping.get("quantity_field_names", ""),
            price_field_names=mapping.get("price_field_names", ""),
            google_sheet_columns=mapping.get("google_sheet_columns", ""),
            required_status_name=mapping.get("required_status_name", ""),
        )

    @app.post("/settings")
    def save_settings():
        new_token = request.form.get("clickup_token", "").strip()
        if new_token:
            storage.set_clickup_token(new_token)
            flash("Token de ClickUp guardado correctamente.", "success")
        
        quantity_names = request.form.get("quantity_field_names", "").strip()
        price_names = request.form.get("price_field_names", "").strip()
        sheet_columns = request.form.get("google_sheet_columns", "").strip()
        required_status = request.form.get("required_status_name", "").strip()
        
        if quantity_names and price_names and sheet_columns and required_status:
            storage.set_field_mapping(quantity_names, price_names, sheet_columns, required_status)
            flash("Mapeo de campos guardado correctamente.", "success")
        
        return redirect(url_for("settings_page"))

    @app.post("/list-config/save")
    def save_list_config():
        """Save per-list Google Sheets configuration."""
        list_id = request.form.get("list_id", "").strip()
        spreadsheet_id = request.form.get("spreadsheet_id", "").strip()
        tab_name = request.form.get("tab_name", "").strip()
        starting_row = request.form.get("starting_row", "").strip()
        
        if not list_id:
            flash("Falta el ID de la lista.", "error")
            return redirect(url_for("dashboard"))
        
        if not spreadsheet_id or not tab_name or not starting_row:
            flash("Faltan campos requeridos.", "error")
            return redirect(url_for("dashboard"))
        
        try:
            starting_row = int(starting_row)
            if starting_row < 1:
                raise ValueError("El número de fila debe ser mayor a 0")
        except ValueError as exc:
            flash(f"Número de fila inválido: {exc}", "error")
            return redirect(url_for("dashboard"))
        
        storage.set_list_config(list_id, spreadsheet_id, tab_name, starting_row)
        flash(f"✓ Configuración guardada", "success")
        return redirect(url_for("dashboard"))

    return app


def build_selection_payload(hierarchy: dict[str, object], selected_space_ids: list[str], selected_folder_ids: list[str], selected_list_ids: list[str]) -> dict[str, list[dict[str, str]]]:
    selected_space_ids_set = set(selected_space_ids)
    selected_folder_ids_set = set(selected_folder_ids)
    selected_list_ids_set = set(selected_list_ids)

    spaces_payload: list[dict[str, str]] = []
    folders_payload: list[dict[str, str]] = []
    lists_payload: list[dict[str, str]] = []

    for space in hierarchy.get("spaces", []):
        if not isinstance(space, dict):
            continue
        space_id = str(space.get("id"))
        space_name = str(space.get("name", space_id))
        space_selected = space_id in selected_space_ids_set
        if space_selected:
            spaces_payload.append({"space_id": space_id, "space_name": space_name})

        for folder in space.get("folders", []):
            if not isinstance(folder, dict):
                continue
            folder_id = str(folder.get("id"))
            folder_name = str(folder.get("name", folder_id))
            folder_selected = folder_id in selected_folder_ids_set
            if folder_selected:
                folders_payload.append(
                    {
                        "space_id": space_id,
                        "space_name": space_name,
                        "folder_id": folder_id,
                        "folder_name": folder_name,
                    }
                )

            for item in folder.get("lists", []):
                if not isinstance(item, dict):
                    continue
                list_id = str(item.get("id"))
                list_name = str(item.get("name", list_id))
                if space_selected or folder_selected or list_id in selected_list_ids_set:
                    lists_payload.append(
                        {
                            "space_id": space_id,
                            "space_name": space_name,
                            "folder_id": folder_id,
                            "folder_name": folder_name,
                            "list_id": list_id,
                            "list_name": list_name,
                        }
                    )

    return {"spaces": spaces_payload, "folders": folders_payload, "lists": lists_payload}


def main() -> None:
    app = create_app()
    port = int(os.getenv("BILLING_PANEL_PORT", "8085"))
    host = os.getenv("BILLING_PANEL_HOST", "0.0.0.0")
    debug = os.getenv("BILLING_PANEL_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
