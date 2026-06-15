from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SAPGHealthCheckGateway:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_database(self) -> bool:
        try:
            await self.session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
