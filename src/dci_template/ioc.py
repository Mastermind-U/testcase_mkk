from typing import AsyncIterator

from dishka import (
    Provider,
    Scope,
    from_context,
    provide,  # pyright: ignore[reportUnknownVariableType]
)
from faststream.kafka import KafkaBroker
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dci_template.application.commands.outbox_processor.gateway import (
    OutboxProcessorGateway,
)
from dci_template.application.commands.outbox_processor.interactor import (
    OutboxProcessorInteractor,
)
from dci_template.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from dci_template.application.queries.healthcheck import (
    HealthCheckGateway,
    HealthCheckInteractor,
)
from dci_template.application.transaction_manager import (
    EntitySaver,
    TransactionManager,
)
from dci_template.config import Config
from dci_template.infrastructure.faststream.publisher import (
    FaststreamKafkaOutboxPublisher,
)
from dci_template.infrastructure.sa.pg.gateways.healthcheck_gw import (
    SAPGHealthCheckGateway,
)
from dci_template.infrastructure.sa.pg.gateways.outbox_processor_gw import (
    SAPGOutboxProcessorGateway,
)
from dci_template.infrastructure.sa.pg.transaction_manager import (
    SAPGEntitySaver,
    SAPGTransactionManager,
)


class MainProvider(Provider):
    config = from_context(Config, scope=Scope.RUNTIME)

    @provide(scope=Scope.RUNTIME)
    def get_engine(self, config: Config) -> AsyncEngine:
        return create_async_engine(config.ENGINE_URL)

    @provide(scope=Scope.APP)
    async def get_kafka_broker(
        self,
        config: Config,
    ) -> AsyncIterator[KafkaBroker]:
        broker = KafkaBroker(bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS)
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
        FaststreamKafkaOutboxPublisher,
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
