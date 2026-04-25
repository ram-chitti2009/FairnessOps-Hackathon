from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # dotenv is optional; env vars can still come from shell/host config.
        pass


@dataclass
class SupabaseConfig:
    url: str
    key: str
    schema: str = "fairnessops"
    prediction_table: str = "prediction_events"

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        _load_dotenv_if_available()
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_KEY", "").strip()
        schema = os.getenv("SUPABASE_SCHEMA", "fairnessops").strip() or "fairnessops"
        table = os.getenv("SUPABASE_PREDICTION_TABLE", "prediction_events").strip() or "prediction_events"

        if not url or not key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_KEY. Set them in environment or .env."
            )

        return cls(url=url, key=key, schema=schema, prediction_table=table)


class SupabaseEventClient:
    """Thin wrapper around supabase-py for inserting prediction events."""

    def __init__(self, config: Optional[SupabaseConfig] = None) -> None:
        self.config = config or SupabaseConfig.from_env()
        try:
            from supabase import Client, create_client  # type: ignore
        except Exception as exc:
            raise ImportError(
                "supabase package is required. Install with: pip install supabase"
            ) from exc

        self._client: Client = create_client(self.config.url, self.config.key)

    def insert_prediction_events(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = list(rows)
        if not payload:
            return []
        result = (
            self._client.schema(self.config.schema)
            .table(self.config.prediction_table)
            .insert(payload)
            .execute()
        )
        # supabase-py returns APIResponse with .data
        return list(result.data or [])
