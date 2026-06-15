import argparse
import asyncio

import uvicorn
from dishka import Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from sqlalchemy import exc as sa_exc
from structlog import get_logger

from payments.config import Config
from payments.entities.exceptions import BaseDomainError, ObjectNotFoundError
from payments.ioc import MainProvider
from payments.presentation.api import routers
from payments.presentation.api.exception_handlers import (
    handle_base_domain_exc,
    handle_db_connect_error,
    handle_obj_not_found,
)
from payments.presentation.faststream.consumer import create_consumer_app
from payments.presentation.outbox_scheduler import (
    create_scheduler_lifespan,
    run_scheduler_loop,
)


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or Config.from_env()
    container = make_async_container(
        MainProvider(),
        start_scope=Scope.RUNTIME,
        context={Config: cfg},
    )
    app = FastAPI(
        debug=cfg.DEBUG,
        lifespan=create_scheduler_lifespan(cfg, container)
        if cfg.DEBUG
        else None,
    )
    app.state.config = cfg

    for router in routers:
        app.include_router(router, prefix="/api/v1")

    app.add_exception_handler(sa_exc.TimeoutError, handle_db_connect_error)
    app.add_exception_handler(sa_exc.InterfaceError, handle_db_connect_error)
    app.add_exception_handler(BaseDomainError, handle_base_domain_exc)
    app.add_exception_handler(ObjectNotFoundError, handle_obj_not_found)

    setup_dishka(container=container, app=app)
    return app


async def run_scheduler(config: Config | None = None) -> None:
    config = config or Config.from_env()
    container = make_async_container(
        MainProvider(),
        context={Config: config},
    )
    await run_scheduler_loop(container, config)


async def run_consumer(config: Config | None = None) -> None:
    config = config or Config.from_env()
    container = make_async_container(
        MainProvider(),
        context={Config: config},
    )
    broker = RabbitBroker(config.RABBITMQ_URL)
    app = create_consumer_app(broker, container)
    try:
        await app.run()
    finally:
        await container.close()


logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="payments",
        description="Run the application or the scheduler.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--app",
        action="store_true",
        help="Run the HTTP application.",
    )
    mode_group.add_argument(
        "--scheduler",
        action="store_true",
        help="Run the outbox scheduler.",
    )
    mode_group.add_argument(
        "--consumer",
        action="store_true",
        help="Run the RabbitMQ consumer.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run through uv run."""
    args = parse_args(argv)
    cfg = Config.from_env()
    if args.scheduler:
        logger.info("Scheduler is starting...")
        asyncio.run(run_scheduler(cfg))
        return

    if args.consumer:
        logger.info("Consumer is starting...")
        asyncio.run(run_consumer(cfg))
        return

    logger.info("Application is starting...")
    uvicorn.run(
        "payments:create_app",
        host=cfg.APP_HOST,
        port=cfg.APP_PORT,
        reload=cfg.DEBUG,
        use_colors=True,
        factory=True,
    )
