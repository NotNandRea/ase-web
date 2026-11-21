"""Database access: the engine and the queries used by the API."""

import os
import uuid
from datetime import timedelta

from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from psycopg.errors import UniqueViolation

from ase_studio import backend
from models import Project, Job, User

url = make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql+psycopg")
engine = create_engine(url)

CHANNEL = "jobs" # the workers LISTEN on this channel
STALE_AFTER = int(os.environ.get("WORKER_STALE_AFTER", "70"))


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

def get_project_by_id(session: Session, project_id: uuid.UUID) -> Project | None:
    """Return the project with that id or None if it was deleted"""
    return session.scalar(select(Project).where(Project.id == project_id))

def rename_project(session: Session, project: Project, new_name: str) -> None:
    """Rename a project, or answer like the original if the user already has one with that name"""
    project.name = new_name
    try:
        session.flush()
    except IntegrityError as error:
        if isinstance(error.orig, UniqueViolation):
            backend.fail("A project with that name already exists.")
        raise
    
def delete_project(session: Session, project: Project) -> None:
    """Delete a project"""
    session.delete(project)
    session.flush()
    
# --- JOBS STUFF ---

def get_active_job(session: Session, owner: uuid.UUID) -> Job | None:
    """Return the user's pending or running job or None"""
    return session.scalar(select(Job).where(
        Job.owner == owner,
        Job.status.in_(("pending", "running"))).limit(1))

def create_job(session: Session, job_id: uuid.UUID, owner: uuid.UUID, kind: str,
               request_key: str, project_id: uuid.UUID | None = None) -> Job:
    """Queue a job and wake the workers, max one pending or running job per user"""
    # Lock the user's row so that a second run request of the same user waits here UNTIL COMMIT
    session.execute(select(User).where(User.id == owner).with_for_update())

    fail_stale_jobs(session, owner)   # a job whose worker died must not block a new Run

    # check if the user has a pending or running job
    if get_active_job(session, owner) is not None:
        backend.fail("A simulation is already running.", 409)

    job = Job(id=job_id, owner=owner, kind=kind, project=project_id, request_key=request_key)
    session.add(job)
    session.flush()

    # notify the workers that a new job is available
    session.execute(text(f"NOTIFY {CHANNEL}"))
    return job

def get_job(session: Session, owner: uuid.UUID, job_id: uuid.UUID) -> Job | None:
    """Return the user's job with that id, or None"""
    return session.scalar(select(Job).where(Job.id == job_id, Job.owner == owner))


def claim_result(session: Session, job: Job) -> bool:
    """True only for the first call that saves the result in the project"""
    claimed = session.scalar(
        update(Job)
        .where(Job.id == job.id, Job.result_saved == False)
        .values(result_saved=True)
        .returning(Job.id))
    if claimed is None:
        return False
    return True

def fail_stale_jobs(session, owner):
    """Mark as failed the running jobs of the user that started too long ago because their worker is dead"""
    session.execute(
        update(Job)
        .where(Job.owner == owner, Job.status == "running",
               Job.started_at < func.now() - timedelta(seconds=STALE_AFTER))
        .values(status="failed")
    )