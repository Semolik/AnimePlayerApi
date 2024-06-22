from datetime import datetime
from src.users_controller import create_user
from src.models.users import User
from sqlalchemy import select
from src.db.session import async_session_maker
from passlib import pwd
from fastapi.logger import logger
from src.core.config import settings


async def init_superuser():
    async with async_session_maker() as session:
        select_first_superuser = select(User).where(User.is_superuser == True)
        result = await session.execute(select_first_superuser)
        has_superuser = result.scalar()
        if not has_superuser:
            password = pwd.genword(length=12, charset="ascii_72")
            email = settings.FIRST_SUPERUSER_EMAIL
            await create_user(email=email, password=password, is_superuser=True, name="Superuser", is_verified=True, register_date=datetime.now())
            logger.warning("Superuser created successfully")
            logger.warning(f"Superuser email: {email}")
            logger.warning(f"Superuser password: {password}")
