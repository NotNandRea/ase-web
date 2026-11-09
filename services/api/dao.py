"""Database access: the engine and the queries used by the API."""

import os
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from psycopg.errors import UniqueViolation

from ase_studio import backend
from models import Project

url = make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql+psycopg")
engine = create_engine(url)


# --- PROJECTS STUFF ---

def create_project(session: Session, owner: uuid.UUID, name: str) -> Project:
    """Insert a project, or answer like the original if the user already has one with that name"""
    project = Project(owner=owner, name=name)
    session.add(project)
    try:
        session.flush()
    except IntegrityError as error: # the database raised an error
        if isinstance(error.orig, UniqueViolation): # the error is a unique violation
            backend.fail("A project with that name already exists.")
        raise
    return project

def list_project_names(session: Session, owner: uuid.UUID) -> list[str]:
    """Return the names of the user's projects, sorted like the original"""
    names = session.scalars(select(Project.name).where(Project.owner == owner))
    return sorted(list(names))

def get_project(session: Session, owner: uuid.UUID, name: str) -> Project | None:
    """Return the project with that name, or None if it does not exist"""
    project = session.scalar(select(Project).where(Project.owner == owner, Project.name == name))
    return project

def rename_project(session: Session, project: Project, new_name: str) -> None:
    """Rename a project, or answer like the original if the user already has one with that name"""
    project.name = new_name
    try:
        session.flush()
    except IntegrityError as error:
        if isinstance(error.orig, UniqueViolation):
            backend.fail("A project with that name already exists.")
        raise