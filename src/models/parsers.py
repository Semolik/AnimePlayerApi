from uuid import uuid4
from src.db.base import Base
from sqlalchemy import UUID,  Column, Integer, String, DateTime, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped


class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_on_website = Column(String, nullable=False)
    parser_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    en_name = Column(String, nullable=True)
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


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title_id = Column(UUID(as_uuid=True), ForeignKey(
        Title.id), nullable=False)
    title = relationship(Title, foreign_keys=[title_id])
    number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    duration = Column(Integer, nullable=True)
    duration_fetched = Column(Boolean, default=False)
    image_url = Column(String)
    links = relationship("EpisodeSource",
                         primaryjoin="Episode.id == EpisodeSource.episode_id", uselist=True)


class EpisodeSource(Base):
    __tablename__ = "episode_sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id = Column(UUID(as_uuid=True), ForeignKey(
        Episode.id), nullable=False)
    link = Column(String, nullable=False)
    name = Column(String, nullable=False)
    quality = Column(Integer, nullable=True)
    is_m3u8 = Column(Boolean, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class EpisodeProgress(Base):
    __tablename__ = "episode_progress"

    episode_id = Column(UUID(as_uuid=True), ForeignKey(
        Episode.id), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), primary_key=True)
    progress = Column(Integer, nullable=False)
    seconds = Column(Integer, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class CurrentEpisode(Base):
    __tablename__ = "current_episodes"

    episode_id = Column(UUID(as_uuid=True), ForeignKey(
        Episode.id), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), primary_key=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


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
