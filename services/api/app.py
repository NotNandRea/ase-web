"""ASE Web API"""

import json
import os
import uuid

import boto3
from fastapi import FastAPI

import models
import schemas

BUCKET = os.environ["S3_BUCKET"]
CHANNEL = "jobs" # the workers LISTEN on this channel

app = FastAPI(title="ASE Web API")
s3 = boto3.client("s3")

# --- MISCELLANEOUS STUFF ---

@app.get("/")
def get_frontend():
    """ Serves the frontend """
    pass

@app.get("/api/health")
def get_health():
    """ Health check endpoint """
    pass

# --- PROJECTS STUFF ---

@app.get("/api/projects")
def get_projects():
    """ Retieves user's projects """
    pass

@app.post("/api/projects")
def create_project():
    """ Creates a new project """
    pass

@app.patch("/api/projects")
def rename_project():
    """ Renames a project """
    pass

@app.delete("/api/projects")
def delete_project():
    """ Deletes a project """
    pass

@app.post("/api/projects/duplicate")
def duplicate_project():
    """ Duplicates a project """
    pass

@app.get("/api/project")
def get_project(name: str):
    """ Retieves a project """
    pass

@app.post("/api/save")
def save_project():
    """ Saves a project """
    pass

@app.post("/api/config")
def save_config():
    """ Saves a project configuration """
    pass

@app.get("/api/config")
def get_config(name: str):
    """ Retieves a project configuration """
    pass

@app.get("/api/pipeline")
def get_pipeline(name: str):
    """ Retieves the last known pipeline for a project """
    pass

@app.get("/api/symbols")
def get_symbols(name: str):
    """ Retieves the last known symbols for a project """
    pass

# --- JOBS STUFF ---

@app.post("/api/run")
def run_job():
    """ Executes a job request """
    pass

@app.get("/api/jobs/{job_id}")
def get_job(job_id: uuid.UUID):
    """ Retieves a job status and, if it is done, its results """
    pass

# --- SUBMISSIONS STUFF ---

@app.post("/api/submit")
def create_submission():
    """ Creates a new submission """
    pass