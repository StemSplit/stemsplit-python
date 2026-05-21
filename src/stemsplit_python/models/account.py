"""Account-related models."""

from __future__ import annotations

from datetime import datetime

from stemsplit_python.models._base import BaseSDKModel


class Balance(BaseSDKModel):
    """Credit balance for the authenticated account.

    Mirrors the shape returned by ``GET /balance``::

        {
          "balanceSeconds": 300,
          "balanceMinutes": 5,
          "balanceFormatted": "5 minutes",
          "updatedAt": "2026-05-21T12:00:00Z"
        }
    """

    balance_seconds: int
    balance_minutes: int
    balance_formatted: str
    updated_at: datetime
