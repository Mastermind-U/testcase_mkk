from typing import Protocol


class PaymentGatewayEmulator(Protocol):
    async def process(self) -> bool: ...
