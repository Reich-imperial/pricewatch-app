from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from common.models import PriceUpdate


def good(**over):
    base = {"schema_version": 1, "event_id": "3f0c2f7e-6b1e-4d0e-9d52-1c2a6a4a9f10",
            "symbol": "RICE_50KG", "price_ngn": 85200,
            "observed_at": "2026-10-28T09:15:30Z", "source": "test"}
    base.update(over)
    return base


def test_valid_update_is_accepted():
    assert PriceUpdate(**good()).price_ngn == 85200


@pytest.mark.parametrize("bad", [
    {"symbol": "GOLD"},
    {"price_ngn": 0},
    {"price_ngn": 85200.5},
    {"observed_at": "2026-10-28T09:15:30"},
    {"observed_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
    {"event_id": "not-a-uuid"},
    {"schema_version": 2},
    {"extra_field": 1},
])
def test_invalid_updates_are_rejected(bad):
    with pytest.raises(ValidationError):
        PriceUpdate(**good(**bad))
