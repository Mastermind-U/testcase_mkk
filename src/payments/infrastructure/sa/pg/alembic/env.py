import asyncio
from logging.config import fileConfig

from alembic import context
from dishka import AsyncContainer, make_async_container
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from payments.config import Config
from payments.infrastructure.sa.pg.tables import metadata
from payments.ioc import MainProvider

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_sync_migrations(
    connection: Connection,
    container: AsyncContainer,
) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=target_metadata.schema,
    )

    with context.begin_transaction():
        context.run_migrations(container=container)


async def run_async_migrations(
    container: AsyncContainer,
) -> None:
    connection = await container.get(AsyncConnection)
    await connection.run_sync(
        run_sync_migrations,
        container=container,
    )


def run_migrations_online() -> None:
    conn = context.config.attributes.get("connection", None)
    config = context.config.attributes.get(
        "app_config",
        Config.from_env(),
    )
    container = context.config.attributes.get("container", None)
    if not container:
        container = make_async_container(
            MainProvider(),
            context={Config: config},
        )

    if conn is None:
        asyncio.run(run_async_migrations(container))
    else:
        run_sync_migrations(
            conn,
            container=container,
        )


run_migrations_online()
