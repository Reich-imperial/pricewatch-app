from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are errors

    schema_version: Literal[1]
    event_id: UUID
    symbol: Literal["RICE_50KG", "BEANS_50KG", "GARRI_50KG", "TOMATO_BASKET", "PALM_OIL_25L"]
    price_ngn: int = Field(strict=True, ge=1, le=10_000_000)  # strict: 85200.5 or "85200" are rejected
    observed_at: datetime
    source: str = Field(min_length=1, max_length=40)

    @field_validator("observed_at")
    @classmethod
    def check_time(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("must include a timezone, use Z for UTC")
        if v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("is more than 5 minutes in the future")
        return v.astimezone(timezone.utc)
class QueuedPriceUpdate(PriceUpdate):
    """ What the worker receives: the API adds received_at. """
    received_at: datetime
