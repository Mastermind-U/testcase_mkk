from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from dishka import (
    AsyncContainer,
    Provider,
    Scope,
    from_context,
    make_async_container,
)
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import (  # pyright: ignore[reportMissingTypeStubs]
    PostgresContainer,
)

from dci_template import create_app
from dci_template.config import Config

POSTGRES_IMAGE = "postgres:15.17-trixie"


class TestProvider(Provider):
    __test__ = False

    scope = Scope.RUNTIME
    settings = from_context(provides=Config, scope=Scope.RUNTIME)
    engine = from_context(provides=AsyncEngine, scope=Scope.RUNTIME)
    sessionmaker = from_context(
        provides=async_sessionmaker[AsyncSession],
        scope=Scope.RUNTIME,
    )
    session = from_context(provides=AsyncSession, scope=Scope.REQUEST)


@pytest.fixture(scope="session")
def default_config() -> Config:
    return Config.from_env()


@pytest.fixture(scope="session")
def postgres_container(default_config: Config) -> Iterator[PostgresContainer]:
    with PostgresContainer(
        POSTGRES_IMAGE,
        username=default_config.POSTGRES_USER,
        password=default_config.POSTGRES_PASSWORD,
        dbname=default_config.POSTGRES_DB,
    ) as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def engine(config: Config) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(config.ENGINE_URL)
    yield eng
    await eng.dispose()


@pytest.fixture
def sessionmaker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest_asyncio.fixture()
async def container(
    config: Config,
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    session: AsyncSession,
) -> AsyncIterator[AsyncContainer]:
    ctnr = make_async_container(
        TestProvider(),
        context={
            Config: config,
            AsyncEngine: engine,
            async_sessionmaker[AsyncSession]: sessionmaker,
            AsyncSession: session,
        },
        start_scope=Scope.RUNTIME,
    )
    yield ctnr
    await ctnr.close()


@pytest.fixture(scope="session")
def config(
    postgres_container: PostgresContainer,
    default_config: Config,
) -> Config:
    return Config(
        DEBUG=default_config.DEBUG,
        APP_HOST=default_config.APP_HOST,
        APP_PORT=default_config.APP_PORT,
        POSTGRES_HOST=postgres_container.get_container_host_ip(),
        POSTGRES_PORT=postgres_container.get_exposed_port(5432),
        POSTGRES_USER=postgres_container.username,
        POSTGRES_PASSWORD=postgres_container.password,
        POSTGRES_DB=postgres_container.dbname,
        POSTGRES_URL_SCHEMA=default_config.POSTGRES_URL_SCHEMA,
    )


@pytest_asyncio.fixture(
    scope="session",
    autouse=True,
)
async def migrations(
    config: Config,
    engine: AsyncEngine,
) -> AsyncIterator[None]:
    al_cfg: AlembicConfig = AlembicConfig("alembic.ini")
    al_cfg.attributes["app_config"] = config

    def upgrade(conn: AsyncConnection) -> None:
        al_cfg.attributes["connection"] = conn
        command.upgrade(al_cfg, "head")

    def downgrade(conn: AsyncConnection) -> None:
        al_cfg.attributes["connection"] = conn
        command.downgrade(al_cfg, "base")

    async with engine.begin() as conn:
        al_cfg.attributes["connection"] = conn
        await conn.run_sync(upgrade)  # type: ignore

    yield

    async with engine.begin() as conn:
        al_cfg.attributes["connection"] = conn
        await conn.run_sync(downgrade)  # type: ignore
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    connection = await engine.connect()
    trans = await connection.begin()

    async_session = sessionmaker(
        bind=connection,
        info={"mode": "test_transaction"},
        join_transaction_mode="create_savepoint",
    )

    yield async_session

    async_session.expire_all()
    await trans.rollback()
    await async_session.close()
    await connection.close()


@pytest_asyncio.fixture()
async def app(
    config: Config,
    container: AsyncContainer,
) -> AsyncIterator[FastAPI]:
    async with container(scope=Scope.APP) as container:
        app = create_app(config)
        setup_dishka(container, app)
        yield app


@pytest.fixture
def http_client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
