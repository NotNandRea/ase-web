"""Database tables, as SQLAlchemy classes.

These classes only DESCRIBE the tables to SQLAlchemy: the tables are created by
db/schema.sql
"""

import uuid
from datetime import datetime

from sqlalchemy import FetchedValue, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    student_id: Mapped[str | None] = mapped_column(unique=True)
    name: Mapped[str]
    last_name: Mapped[str]
    
class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    owner: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=FetchedValue())
    owner: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str]
    project: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(server_default=FetchedValue())
    request_key: Mapped[str]
    result_key: Mapped[str | None]
    result_saved: Mapped[bool] = mapped_column(server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(server_default=FetchedValue())
    started_at: Mapped[datetime | None]