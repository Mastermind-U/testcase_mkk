from dishka import AsyncContainer
from dishka_faststream import setup_dishka
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from payments.presentation.faststream.routes import router


def create_consumer_app(
    broker: RabbitBroker,
    container: AsyncContainer,
) -> FastStream:
    broker.include_router(router)
    app = FastStream(broker)
    setup_dishka(container=container, app=app, auto_inject=True)
    return app
