from typing import List
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyBaseOAuthAccountTableUUID
from src.db.base import Base
from sqlalchemy import UUID, Boolean, Column, String, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, relationship, declared_attr,mapped_column


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):

    @declared_attr
    def user_id(cls):
        return mapped_column(UUID, ForeignKey("users.id", ondelete="cascade"), nullable=False)

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    name = Column(String, nullable=False)
    register_date = Column(DateTime(timezone=True), server_default=func.now())
    oauth_accounts: Mapped[List[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )
