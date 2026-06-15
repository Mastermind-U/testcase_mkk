import asyncio
import random


class RandomPaymentGatewayEmulator:
    async def process(self) -> bool:
        await asyncio.sleep(random.uniform(2, 5))
        return random.random() < 0.9
