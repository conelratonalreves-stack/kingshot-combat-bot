from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from unicodedata import normalize

import requests


@dataclass
class ClickUpNode:
    id: str
    name: str
    tasks: list[dict[str, Any]] | None = None
    lists: list[dict[str, Any]] | None = None


class ClickUpClient:
    """Thin wrapper around the ClickUp API used by the billing panel."""

    def __init__(self, token: str, team_id: str | None = None) -> None:
        self.token = token
        self.team_id = team_id
        self.base_url = "https://api.clickup.com/api/v2"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": token, "Content-Type": "application/json"})

    @classmethod
    def from_env(cls) -> "ClickUpClient | None":
        token = os.getenv("CLICKUP_API_TOKEN") or os.getenv("CLICKUP_TOKEN")
        if not token:
            return None
        team_id = os.getenv("CLICKUP_TEAM_ID")
        return cls(token=token, team_id=team_id)

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.request(method, f"{self.base_url}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def list_teams(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/team")
        return payload.get("teams", [])

    def list_spaces(self, team_id: str | None = None) -> list[dict[str, Any]]:
        team = team_id or self.team_id or self._fallback_team_id()
        payload = self._request("GET", f"/team/{team}/space")
        return payload.get("spaces", [])

    def list_folders(self, space_id: str) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/space/{space_id}/folder")
        return payload.get("folders", [])

    def list_lists_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/folder/{folder_id}/list")
        return payload.get("lists", [])

    def list_lists_in_space(self, space_id: str) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/space/{space_id}/list")
        return payload.get("lists", [])

    def list_tasks(self, list_id: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        page = 0
        while True:
            payload = self._request(
                "GET",
                f"/list/{list_id}/task",
                params={"page": page, "include_closed": "true"},
            )
            batch = payload.get("tasks", [])
            tasks.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return tasks

    def discover_hierarchy(self, team_id: str | None = None) -> dict[str, Any]:
        resolved_team = team_id or self.team_id or self._fallback_team_id()
        spaces = []
        for space in self.list_spaces(resolved_team):
            if self._is_private_space(space):
                continue
            folders = []
            folder_payloads = self.list_folders(space["id"])
            if folder_payloads:
                for folder in folder_payloads:
                    lists = self.list_lists_in_folder(folder["id"])
                    folders.append(
                        {
                            "id": str(folder["id"]),
                            "name": folder.get("name", folder["id"]),
                            "lists": [
                                {
                                    "id": str(item["id"]),
                                    "name": item.get("name", item["id"]),
                                    "task_count": item.get("task_count", 0),
                                }
                                for item in lists
                            ],
                        }
                    )
            else:
                lists = self.list_lists_in_space(space["id"])
                folders.append(
                    {
                        "id": f"space:{space['id']}",
                        "name": "Sin carpeta",
                        "lists": [
                            {
                                "id": str(item["id"]),
                                "name": item.get("name", item["id"]),
                                "task_count": item.get("task_count", 0),
                            }
                            for item in lists
                        ],
                    }
                )
            spaces.append(
                {
                    "id": str(space["id"]),
                    "name": space.get("name", space["id"]),
                    "folders": folders,
                }
            )
        return {"team_id": str(resolved_team), "spaces": spaces}

    @staticmethod
    def _is_private_space(space: dict[str, Any]) -> bool:
        """Best-effort detection of private spaces from ClickUp payload."""
        if bool(space.get("private")):
            return True

        privacy_value = str(space.get("privacy", "")).strip().lower()
        if privacy_value == "private":
            return True

        access_value = str(space.get("access", "")).strip().lower()
        if access_value == "private":
            return True

        return False

    def _fallback_team_id(self) -> str:
        teams = self.list_teams()
        if not teams:
            raise RuntimeError("No ClickUp teams found for the configured token.")
        return str(teams[0]["id"])

    @staticmethod
    def _normalize_field_name(value: str) -> str:
        normalized = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower().strip()
        normalized = re.sub(r"[_\-]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    @staticmethod
    def extract_custom_field(task: dict[str, Any], field_candidates: list[str]) -> Any:
        custom_fields = task.get("custom_fields", []) or []
        normalized_candidates = {
            ClickUpClient._normalize_field_name(candidate)
            for candidate in field_candidates
            if candidate and candidate.strip()
        }
        for field in custom_fields:
            field_id = str(field.get("id", "")).strip().lower()
            field_name = ClickUpClient._normalize_field_name(str(field.get("name", "")))
            if field_id in normalized_candidates or field_name in normalized_candidates:
                return field.get("value")
        return None

    @staticmethod
    def parse_decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, dict):
            for key in ("value", "amount", "number"):
                if key in value:
                    value = value.get(key)
                    break
        try:
            raw = str(value).strip()
            if not raw:
                return None

            # Keep only digits and separators to support strings like "€10".
            cleaned = re.sub(r"[^0-9,\.\-]", "", raw)
            if not cleaned or cleaned in {"-", ".", ","}:
                return None

            if "," in cleaned and "." in cleaned:
                # Use the last separator as decimal marker and treat the other as thousands.
                if cleaned.rfind(",") > cleaned.rfind("."):
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                else:
                    cleaned = cleaned.replace(",", "")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")

            return Decimal(cleaned)
        except Exception:
            return None
