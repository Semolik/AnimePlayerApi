from typing import List
from uuid import uuid4
from src.db.base import Base
from sqlalchemy import UUID, Boolean, Column, String, DateTime, func

class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_on_website = Column(String, nullable=False, unique=True)
    parser_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    page_fetched = Column(Boolean, default=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    description = Column(String)
    image_url = Column(String)
    

class Genre(Base):
    __name__ = "genres"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_on_website = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(String)
    parser_id = Column(String, nullable=False)
