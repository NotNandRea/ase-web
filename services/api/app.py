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


CHANNEL = "jobs" # the workers LISTEN on this channel

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
def delete_project(owner: uuid.UUID = Depends(current_user)):
    """ Deletes a project """
    pass

@app.post("/api/projects/duplicate")
def duplicate_project(owner: uuid.UUID = Depends(current_user)):
    """ Duplicates a project """
    pass

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
            backend.fail("Project not found.")
        last_run = storage.read_last_run(project)

    if last_run is None:
        backend.fail("No trace has been generated for this project.")

    return last_run["pipeline"]

@app.get("/api/symbols")
def get_symbols(name: str, owner: uuid.UUID = Depends(current_user)):
    """ Retieves the last known symbols for a project """
    
    name = backend.validate_project_name(name)
    
    with Session(dao.engine) as session, session.begin():
        project = dao.get_project(session, owner, name)
        if project is None:
            backend.fail("Project not found.")
        last_run = storage.read_last_run(project)
    
    if last_run is None:
        return {"symbols": [], "initialMemory": {}, "memoryMap": []}
    
    symbols = last_run["pipeline"]["dataSymbols"]
    initialMemory = last_run["pipeline"]["initialMemory"]
    memoryMap = last_run["pipeline"]["memoryMap"]
    
    return {"symbols": symbols, "initialMemory": initialMemory, "memoryMap": memoryMap}
        

# --- JOBS STUFF ---

@app.post("/api/run")
def run_job(owner: uuid.UUID = Depends(current_user)):
    """ Executes a job request """
    pass

@app.get("/api/jobs/{job_id}")
def get_job(job_id: uuid.UUID, owner: uuid.UUID = Depends(current_user)):
    """ Retieves a job status and, if it is done, its results """
    pass

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