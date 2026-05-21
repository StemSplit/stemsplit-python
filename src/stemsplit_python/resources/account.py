"""Account / balance endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stemsplit_python.models.account import Balance

if TYPE_CHECKING:
    from stemsplit_python._transport import Transport


class AccountResource:
    """``GET /balance``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def balance(self) -> Balance:
        """Return the credit balance for the authenticated account."""

        data = self._transport.request("GET", "/balance")
        return Balance.model_validate(data)

    def get(self) -> Balance:
        """Alias for :meth:`balance`. Mirrors the brief's ``client.account.get()``."""

        return self.balance()


__all__ = ["AccountResource"]
