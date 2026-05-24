from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


class SheetsClient:
    """Google Sheets writer used by the billing panel."""

    def __init__(self, spreadsheet_id: str | None = None, worksheet_name: str | None = None, credentials_file: str | None = None) -> None:
        self.spreadsheet_id = spreadsheet_id or ""
        self.worksheet_name = worksheet_name or ""
        self.credentials_file = credentials_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not self.credentials_file:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is required for Google Sheets access.")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = service_account.Credentials.from_service_account_file(self.credentials_file, scopes=scopes)
        self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    @classmethod
    def from_env(cls) -> "SheetsClient | None":
        credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_file:
            return None
        return cls(credentials_file=credentials_file)

    @staticmethod
    def _decimal_to_number(value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def append_row(self, row: list[Any]) -> dict[str, Any]:
        range_name = f"{self.worksheet_name}!A:Z"
        body = {"values": [row]}
        response = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return response

    def append_row_to_spreadsheet(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        row_data: dict[str, Any],
        starting_row: int = 1,
    ) -> dict[str, Any]:
        """
        Write a row to a specific spreadsheet with custom cell mapping.
        
        row_data format: {'cantidad': value, 'descripcion': value, 'precio_unitario': value}
        Maps to: B (cantidad), C (descripcion), F (precio_unitario) starting from starting_row
        """
        # Map columns: B=cantidad, C=descripcion, F=precio_unitario
        column_map = {
            'cantidad': 'B',
            'descripcion': 'C',
            'precio_unitario': 'F',
        }
        
        updates = []
        for col_name, col_letter in column_map.items():
            value = row_data.get(col_name)
            if value is not None:
                if isinstance(value, Decimal):
                    value = self._decimal_to_number(value)
                cell_reference = f"{worksheet_name}!{col_letter}{starting_row}"
                updates.append({
                    'range': cell_reference,
                    'values': [[value]],
                })
        
        if not updates:
            raise ValueError("No data to write")
        
        body = {'data': updates, 'valueInputOption': 'USER_ENTERED'}
        response = self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body,
        ).execute()
        
        return response
