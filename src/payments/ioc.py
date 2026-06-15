from typing import AsyncIterator

from dishka import (
    Provider,
    Scope,
    from_context,
    provide,  # pyright: ignore[reportUnknownVariableType]
)
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from payments.application.commands.outbox_processor.gateway import (
    OutboxProcessorGateway,
)
from payments.application.commands.outbox_processor.interactor import (
    OutboxProcessorInteractor,
)
from payments.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from payments.application.queries.healthcheck import (
    HealthCheckGateway,
    HealthCheckInteractor,
)
from payments.application.transaction_manager import (
    EntitySaver,
    TransactionManager,
)
from payments.config import Config
from payments.infrastructure.faststream.publisher import (
    FaststreamRabbitOutboxPublisher,
)
from payments.infrastructure.sa.pg.gateways.healthcheck_gw import (
    SAPGHealthCheckGateway,
)
from payments.infrastructure.sa.pg.gateways.outbox_processor_gw import (
    SAPGOutboxProcessorGateway,
)
from payments.infrastructure.sa.pg.transaction_manager import (
    SAPGEntitySaver,
    SAPGTransactionManager,
)


class MainProvider(Provider):
    config = from_context(Config, scope=Scope.RUNTIME)

    @provide(scope=Scope.RUNTIME)
    def get_engine(self, config: Config) -> AsyncEngine:
        return create_async_engine(config.ENGINE_URL)

    @provide(scope=Scope.APP)
    async def get_rabbit_broker(
        self,
        config: Config,
    ) -> AsyncIterator[RabbitBroker]:
        broker = RabbitBroker(config.RABBITMQ_URL)
        await broker.connect()
        yield broker
        await broker.stop()

    @provide(scope=Scope.APP)
    def get_sessionmaker(
        self,
        engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    healthcheck_gw = provide(
        SAPGHealthCheckGateway,
        provides=HealthCheckGateway,
        scope=Scope.REQUEST,
    )
    outbox_gw = provide(
        SAPGOutboxProcessorGateway,
        provides=OutboxProcessorGateway,
        scope=Scope.REQUEST,
    )
    outbox_publisher = provide(
        FaststreamRabbitOutboxPublisher,
        provides=OutboxPublisher,
        scope=Scope.APP,
    )
    transaction_manager = provide(
        SAPGTransactionManager,
        provides=TransactionManager,
        scope=Scope.REQUEST,
    )
    entity_saver = provide(
        SAPGEntitySaver,
        provides=EntitySaver,
        scope=Scope.REQUEST,
    )
    healthcheck_int = provide(HealthCheckInteractor, scope=Scope.REQUEST)
    outbox_processor_int = provide(
        OutboxProcessorInteractor,
        scope=Scope.REQUEST,
    )

    @provide(scope=Scope.APP)
    async def get_conn(
        self,
        engine: AsyncEngine,
    ) -> AsyncIterator[AsyncConnection]:
        async with engine.connect() as connection:
            yield connection
