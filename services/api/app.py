"""ASE Web API"""

import json
import os
import uuid

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ase_studio import backend

from models import User, Project, Job
import dao
from sqlalchemy.orm import Session

import storage

from schemas import CreateProject, RenameProject, DeleteProject, DuplicateProject, SaveProject, SaveConfig, RunJob, JobCreated, JobStatus

from auth import current_user


app = FastAPI(title="ASE Web API")

# --- MISCELLANEOUS STUFF ---

@app.get("/api/health")
def get_health():
    """ Returns a dictionary with the used versions """
    return {"ok": True, "apiVersion": backend.STUDIO_API_VERSION,
            "version": backend.STUDIO_VERSION,
            "o3Defaults": backend.DEFAULT_O3_CONFIG,
            "features": {
                "developerMode": backend.DEVELOPER_MODE,
                "memoryConfiguration": backend.ENABLE_MEMORY_CONFIGURATION,
                "multiIssueCpu": backend.ENABLE_MULTI_ISSUE_CPU,
            }
        }

# --- PROJECTS STUFF ---

@app.get("/api/projects")
def get_projects(owner: uuid.UUID = Depends(current_user)):
    """ Retieves user's projects """
    
    with Session(dao.engine) as session, session.begin():
        projects = dao.list_project_names(session, owner)
    
    return {"projects": projects}

@app.post("/api/projects")
def create_project(body: CreateProject, owner: uuid.UUID = Depends(current_user)):
    """ Creates a new project """
    
    name = backend.validate_project_name(body.name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.create_project(session, owner, name)
        storage.write_source(project, backend.TEMPLATE)
    
    return {"ok": True, "name": name}

@app.patch("/api/projects")
def rename_project(body: RenameProject, owner: uuid.UUID = Depends(current_user)):
    """ Renames a project """
    
    oldName = backend.validate_project_name(body.name)
    newName = backend.validate_project_name(body.newName)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, oldName)
        if project is None:
            backend.fail("This project does not exist.")
        dao.rename_project(session, project, newName)
    
    return {"ok": True, "name": newName}

@app.delete("/api/projects")
def delete_project(body: DeleteProject, owner: uuid.UUID = Depends(current_user)):
    """Delete a project and all its files"""
    if body.confirmation != body.name:
        backend.fail("Project deletion was not confirmed.")
    name = backend.validate_project_name(body.name)

    # expire_on_commit=False: project.owner and project.id are accessible after commit
    with Session(dao.engine, expire_on_commit=False) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("Project not found.", 404)
        dao.delete_project(session, project)

    # After the commit so even if s3 fails, the project is still deleted from the database
    storage.delete_project(project)
    return {"ok": True}

@app.post("/api/projects/duplicate")
def duplicate_project(body: DuplicateProject, owner: uuid.UUID = Depends(current_user)):
    """Duplicate a project without its last run"""
    new_name = backend.validate_project_name(body.newName)

    with Session(dao.engine) as session, session.begin():
        source = dao.get_project(session, owner, body.name)
        if source is None:
            backend.fail("Project not found.", 404)
        copy = dao.create_project(session, owner, new_name)
        storage.copy_project_files(source, copy)

    return {"ok": True, "name": new_name}

@app.get("/api/project")
def get_project(name: str, owner: uuid.UUID = Depends(current_user)):
    """ Retieves a project """
    name = backend.validate_project_name(name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("This project does not exist.")
        source = storage.read_source(project)
        config = storage.read_config(project)
    
    source = backend.clean_source(source)

    return {"name": name,
            "sourceName": storage.SOURCE_FILE,
            "text": source,
            "protectedLines": backend.protected_lines(source),
            "isa": backend.riscv_isa_for_config(config),
            "config": config,
            }

@app.post("/api/save")
def save_project(body: SaveProject, owner: uuid.UUID = Depends(current_user)):
    """ Saves a project """
    name = backend.validate_project_name(body.name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("This project does not exist.")
        storage.save_source(project, body.text, body.allowScaffoldEdit)
    
    return {"ok": True}
    

@app.post("/api/config")
def save_config(body: SaveConfig, owner: uuid.UUID = Depends(current_user)):
    """ Saves a project configuration """
    
    name = backend.validate_project_name(body.name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("This project does not exist.")
        config = backend.validate_config(body.config)
        storage.save_config(project, config)
        
    return config

@app.get("/api/config")
def get_config(name: str, owner: uuid.UUID = Depends(current_user)):
    """ Retieves a project configuration """
    
    name = backend.validate_project_name(name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("This project does not exist.")
        config = storage.read_config(project)
        
    return config

@app.get("/api/pipeline")
def get_pipeline(name: str, owner: uuid.UUID = Depends(current_user)):
    """ Retieves the last known pipeline for a project """
    
    name = backend.validate_project_name(name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("Project not found.", 404)
        last_run = storage.read_last_run(project)

    if last_run is None:
        backend.fail("No trace has been generated for this project.", 404)

    return last_run["pipeline"]

@app.get("/api/symbols")
def get_symbols(name: str, owner: uuid.UUID = Depends(current_user)):
    """ Retieves the last known symbols for a project """
    
    name = backend.validate_project_name(name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("Project not found.", 404)
        last_run = storage.read_last_run(project)
    
    if last_run is None:
        return {"symbols": [], "initialMemory": {}, "memoryMap": []}
    
    symbols = last_run["pipeline"]["dataSymbols"]
    initialMemory = last_run["pipeline"]["initialMemory"]
    memoryMap = last_run["pipeline"]["memoryMap"]
    
    return {"symbols": symbols, "initialMemory": initialMemory, "memoryMap": memoryMap}
        

# --- JOBS STUFF ---

@app.post("/api/run")
def run_job(body: RunJob, owner: uuid.UUID = Depends(current_user)):
    """Queue a simulation of a project"""
    name = backend.validate_project_name(body.name)
    job_id = uuid.uuid4()
    request_key = storage.job_key(job_id, storage.REQUEST_FILE)

    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("Project not found.", 404)
        
        dao.create_job(session, job_id, owner, "run", request_key, project.id)
        storage.save_source(project, body.text, body.allowScaffoldEdit)

        # What the worker needs to run the original backend
        request = {
            "name": name,
            "text": body.text,
            "config": storage.read_config(project),
            "allowScaffoldEdit": body.allowScaffoldEdit,
        }
        storage.write_request(job_id, request)

    return {"jobId": job_id}

@app.get("/api/jobs/{job_id}")
def get_job(job_id: uuid.UUID, owner: uuid.UUID = Depends(current_user)):
    """Return the state of a job and, when it is done, its result"""
    
    with Session(dao.engine) as session, session.begin():
        job = dao.get_job(session, owner, job_id)
        if job is None:
            backend.fail("Job not found.", 404)
        
        status = job.status
        result = None
        
        if status == "done":
            result = storage.read_result(job)
            if result is None:
                backend.fail("The result of this job is no longer available.", 404)
            
            # The first time a successful run is read it becomes the project's last run
            if job.kind == "run" and result.get("ok") and dao.claim_result(session, job):
                project = dao.get_project_by_id(session, job.project)
                if project is not None:
                    storage.write_last_run(project, result)

    return {"id": job_id, "status": status, "result": result}

# --- SUBMISSIONS STUFF ---

@app.post("/api/submit")
def create_submission(owner: uuid.UUID = Depends(current_user)):
    """ Creates a new submission """
    pass

# --- FRONTEND STUFF ---

app.mount("/", StaticFiles(directory=backend.FRONTEND, html=True), name="frontend")

# --- EXCEPTIONS STUFF ---

@app.exception_handler(ValueError)
def backend_error(request: Request, error: ValueError):
    """Answer like the original backend: {"error": message} with its status code, called by the backend.fail() function"""
    message, status = error.args[0]
    return JSONResponse({"error": message}, status_code=status)


@app.exception_handler(Exception)
def unexpected_error(request: Request, error: Exception):
    """Answer unexpected errors in the original format, without internal details."""
    return JSONResponse({"error": "Internal server error."}, status_code=500)