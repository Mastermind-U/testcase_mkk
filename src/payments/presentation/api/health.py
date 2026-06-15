from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status

from payments.application.queries.healthcheck.interactor import (
    HealthCheckInteractor,
)

from .schemas import StatusResponse

router = APIRouter(prefix="/health", tags=["health"], route_class=DishkaRoute)


@router.get("/")
async def health_check(
    interactor: FromDishka[HealthCheckInteractor],
) -> StatusResponse:
    """Health check endpoint."""
    st = await interactor.execute()
    if st.status != "OK":  # pyright: ignore[reportUnnecessaryComparison]
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE)
    return StatusResponse(status=True)
