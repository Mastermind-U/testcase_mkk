from typing import NoReturn

from fastapi import HTTPException, Request, status
from structlog import get_logger
from structlog.stdlib import BoundLogger

logger: BoundLogger = get_logger()


def handle_db_connect_error(
    request: Request,  # noqa: ARG001
    exc: Exception,
) -> NoReturn:
    if "QueuePool limit of size" in str(exc):
        logger.critical("POOL EXCEEDED {}", exc)

        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Connection Pool Exceeded",
        )

    logger.critical("DB BACKEND ERR {}", exc)

    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE)


def handle_base_domain_exc(request: Request, exc: Exception) -> NoReturn:  # noqa: ARG001
    raise HTTPException(status.HTTP_400_BAD_REQUEST)


def handle_obj_not_found(request: Request, exc: Exception) -> NoReturn:  # noqa: ARG001
    raise HTTPException(status.HTTP_404_NOT_FOUND)
