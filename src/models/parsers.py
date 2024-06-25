from typing import List
from uuid import uuid4
from src.db.base import Base
from sqlalchemy import UUID,  Column, Integer, String, DateTime, func, ForeignKey, Boolean


class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_on_website = Column(String, nullable=False, unique=True)
    parser_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    shikimori_fetched = Column(Boolean, default=False)
    shikimori_id = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    image_url = Column(String)


class FavoriteTitle(Base):
    __tablename__ = "favorite_titles"

    title_id = Column(UUID(as_uuid=True), ForeignKey(
        Title.id), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), primary_key=True)
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Genre(Base):
    __name__ = "genres"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_on_website = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    parser_id = Column(String, nullable=False)


class RelatedLink(Base):
    __tablename__ = "related_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class RelatedTitle(Base):
    __tablename__ = "related_titles"

    link_id = Column(UUID(as_uuid=True), ForeignKey(
        RelatedLink.id), primary_key=True)
    title_id = Column(UUID(as_uuid=True), ForeignKey(
        Title.id), primary_key=True)
