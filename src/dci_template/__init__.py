import argparse
import asyncio

import uvicorn
from dishka import Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from sqlalchemy import exc as sa_exc
from structlog import get_logger

from dci_template.config import Config
from dci_template.entities.exceptions import (
    BaseDomainError,
    ObjectNotFoundError,
)
from dci_template.ioc import MainProvider
from dci_template.presentation.api import routers
from dci_template.presentation.api.exception_handlers import (
    handle_base_domain_exc,
    handle_db_connect_error,
    handle_obj_not_found,
)
from dci_template.presentation.outbox_scheduler import (
    create_scheduler_lifespan,
    run_scheduler_loop,
)


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or Config()
    container = make_async_container(
        MainProvider(),
        start_scope=Scope.RUNTIME,
        context={Config: cfg},
    )
    app = FastAPI(
        root_path="/api/v1",
        debug=cfg.DEBUG,
        lifespan=create_scheduler_lifespan(cfg, container)
        if cfg.DEBUG
        else None,
    )

    for router in routers:
        app.include_router(router)

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


logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dci_template",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run through uv run."""
    args = parse_args(argv)
    cfg = Config.from_env()
    if args.scheduler:
        logger.info("Scheduler is starting...")
        asyncio.run(run_scheduler(cfg))

    logger.info("Application is starting...")
    uvicorn.run(
        "dci_template:create_app",
        host=cfg.APP_HOST,
        port=cfg.APP_PORT,
        reload=cfg.DEBUG,
        use_colors=True,
        factory=True,
    )
