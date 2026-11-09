"""Shape of the API requests and responses (Pydantic models)"""

import uuid

from pydantic import BaseModel

# --- PROJECT STUFF ---

class CreateProject(BaseModel):
    """Body of POST /api/projects"""
    
    name: str
    
class RenameProject(BaseModel):
    """Body of PATCH /api/projects"""
    
    name: str
    newName: str

class DeleteProject(BaseModel):
    """Body of DELETE /api/projects"""
    
    name: str
    confirmation: str

class DuplicateProject(BaseModel):
    """Body of POST /api/projects/duplicate"""
    
    name: str
    newName: str

class SaveProject(BaseModel):
    """Body of POST /api/save"""
    
    name: str
    text: str
    allowScaffoldEdit: bool = False
    
class SaveConfig(BaseModel):
    """Body of POST /api/config"""
    
    name: str
    config: dict

# --- JOBS STUFF ---

class RunJob(BaseModel):
    """Body of POST /api/run"""
    
    name: str
    text: str
    allowScaffoldEdit: bool = False

class JobCreated(BaseModel):
    """Response of POST /api/run"""

    jobId: uuid.UUID


class JobStatus(BaseModel):
    """Response of GET /api/jobs/{job_id}"""

    id: uuid.UUID
    status: str
    result: dict | None = None

# --- SUBMISSIONS STUFF ---

class SubmissionProject(BaseModel):
    """One project inside the body of POST /api/submit"""

    name: str
    source: str | None = None
    allowScaffoldEdit: bool = False


class CreateSubmission(BaseModel):
    """Body of POST /api/submit"""

    projects: list[SubmissionProject]
    assignment: str
    attachments: list[dict] | None = None
    expandLoops: bool = False