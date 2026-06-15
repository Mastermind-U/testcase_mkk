from collections.abc import AsyncIterator

import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrations() -> AsyncIterator[None]:  # pyright: ignore[reportUnusedFunction]
    yield
