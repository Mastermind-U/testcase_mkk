from typing import Any, cast

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from payments.infrastructure.sa.pg.gateways.payments_gw import (
    SAPGPaymentGateway,
)


class SessionFake:
    def __init__(self) -> None:
        self.statement: Select[Any] | None = None

    async def scalar(self, statement: Select[Any]) -> None:
        self.statement = statement


async def test_get_by_idempotency_key_uses_for_update() -> None:
    session = SessionFake()
    gw = SAPGPaymentGateway(cast("AsyncSession", session))

    await gw.get_by_idempotency_key("key-1")

    assert session.statement is not None
    compiled = session.statement.compile(dialect=postgresql.dialect())
    assert "FOR UPDATE" in str(compiled)
