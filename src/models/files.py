from src.db.base import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from uuid import uuid4


class Image(Base):
    __tablename__ = 'images'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
