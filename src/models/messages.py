from uuid import uuid4
from src.db.base import Base
from sqlalchemy import UUID, Column, Integer,  String, DateTime, func


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content = Column(String, nullable=False)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
