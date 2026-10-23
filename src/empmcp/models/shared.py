"""Shared model helpers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator


def _to_date(value: Any) -> Any:
    # Oracle DATE columns come back as datetime; the API exposes plain dates.
    return value.date() if isinstance(value, datetime) else value


DateOnly = Annotated[date, BeforeValidator(_to_date)]
