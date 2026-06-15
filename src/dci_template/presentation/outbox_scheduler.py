from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from dishka import AsyncContainer, Scope
from fastapi import FastAPI
from starlette.types import Lifespan
from structlog import get_logger

from dci_template.application.commands.outbox_processor.interactor import (
    OutboxProcessorInteractor,
)
from dci_template.config import Config

_logger = get_logger(source="scheduler")


def create_scheduler_lifespan(
    config: Config,
    container: AsyncContainer,
) -> Lifespan[FastAPI]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
        scheduler_task = asyncio.create_task(
            run_scheduler_loop(container, config),
            name="outbox-scheduler",
        )

        yield

        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task
        await container.close()
        _logger.info("Scheduler shutdown")

    return lifespan


async def run_scheduler_loop(
    container: AsyncContainer,
    config: Config,
) -> None:
    _logger.info("Scheduler started")
    while True:
        await asyncio.sleep(config.OUTBOX_SCHEDULER_INTERVAL_SECONDS)
        async with container(scope=Scope.REQUEST) as r_c:
            interactor = await r_c.get(OutboxProcessorInteractor)
            await interactor.execute(config.OUTBOX_SCHEDULER_BATCH_SIZE)
