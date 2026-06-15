from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Depends, Header, HTTPException, status

from payments.application.commands.payments import (
    CreatePaymentInput,
    CreatePaymentInteractor,
)
from payments.application.queries.payments import ReadPaymentInteractor
from payments.config import Config

from .schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentResponse,
)

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    route_class=DishkaRoute,
)


@inject
def verify_api_key(
    config: FromDishka[Config],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if x_api_key != config.API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
)
async def create_payment(
    request: CreatePaymentRequest,
    interactor: FromDishka[CreatePaymentInteractor],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1),
    ],
) -> CreatePaymentResponse:
    payment = await interactor.execute(
        CreatePaymentInput(
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            metadata=request.metadata,
            webhook_url=str(request.webhook_url)
            if request.webhook_url is not None
            else None,
            idempotency_key=idempotency_key,
        ),
    )
    return CreatePaymentResponse.from_dto(payment)


@router.get(
    "/{payment_id}",
    dependencies=[Depends(verify_api_key)],
)
async def get_payment(
    payment_id: UUID,
    interactor: FromDishka[ReadPaymentInteractor],
) -> PaymentResponse:
    payment = await interactor.execute(payment_id)
    return PaymentResponse.from_dto(payment)
