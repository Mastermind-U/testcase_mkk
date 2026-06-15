from .health import router as health_router
from .payments import router as payments_router

routers = [
    health_router,
    payments_router,
]
