"""S3 access: where files live, and how to read and write them"""

import json
import os
import uuid
import copy

import boto3

from ase_studio import backend
from models import Job, Project


BUCKET = os.environ["S3_BUCKET"]
s3 = boto3.client("s3")
SOURCE_FILE = "main.s"
CONFIG_FILE = ".ase-studio.json"
LAST_RUN_FILE = "last-run/result.json"
LAST_RUN_CSV_FILE = "last-run/pipeline-full.csv"
REQUEST_FILE = "request.json"

# --- S3 CORE FEATURES ---

def read_text(key: str) -> str | None:
    """Read a text file from S3, or None if it does not exist"""
    try:
        return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        return None

def read_json(key: str) -> dict | None:
    """Read a JSON file from S3, or None if it does not exist"""
    text = read_text(key)
    if text is None:
        return None
    return json.loads(text)

def write_text(key: str, text: str) -> None:
    """Write a text file to S3"""
    s3.put_object(Bucket=BUCKET, Key=key, Body=text.encode())

def delete_prefix(prefix: str) -> None:
    """Delete every file that has the key starting with this prefix"""
    listing = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for item in listing.get("Contents", []):
        s3.delete_object(Bucket=BUCKET, Key=item["Key"])

# --- KEY CREATION ---

def project_key(project: Project, filename: str) -> str:
    """S3 key of one file of a project"""
    return f"users/{project.owner}/projects/{project.id}/{filename}"

def job_key(job_id: uuid.UUID, filename: str) -> str:
    """S3 key of one file of a job"""
    return f"jobs/{job_id}/{filename}"

# --- SOURCE STUFF ---

def write_source(project: Project, text: str) -> None:
    """Write the project's assembly source"""
    write_text(project_key(project, SOURCE_FILE), text)

def read_source(project: Project) -> str:
    """Read the project's assembly source"""
    text = read_text(project_key(project, SOURCE_FILE))
    if text is None:
        backend.fail("This project has no assembly source file.")
    return text

def save_source(project: Project, submitted: str, allow_scaffold_edit: bool = False) -> None:
    """Save the project's source, like the original save_source: protected lines cannot change"""
    existing = backend.clean_source(read_source(project))
    submitted = backend.clean_source(submitted)
    if (not allow_scaffold_edit and backend.mandatory_signature(existing) != backend.mandatory_signature(submitted)):
        backend.fail("The mandatory entry or exit instructions cannot be changed.")
    write_source(project, submitted)

# --- CONFIG STUFF ---

def read_config(project: Project) -> dict:
    """Read the project's CPU configuration, like the original project_config"""
    text = read_text(project_key(project, CONFIG_FILE))
    if text is None:
        return backend.DEFAULT_CONFIG.copy()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        backend.fail("The project CPU configuration is invalid.")
    return backend.validate_config(value)

def save_config(project: Project, config: dict) -> None:
    """Save the project's CPU configuration, like the original save_project_config"""
    # Indentation and final newline are cosmetic, but keep the file readable like the original backend
    write_text(project_key(project, CONFIG_FILE), json.dumps(config, indent=2) + "\n")

# --- PROJECT STUFF ---

def delete_project(project: Project) -> None:
    """Delete all the files of a project"""
    delete_prefix(project_key(project, ""))

def copy_project_files(source: Project, destination: Project) -> None:
    """Copy files of project, like the original duplicate_project, not the last run"""
    # source
    text = read_text(project_key(source, SOURCE_FILE))
    if text is not None:
        write_text(project_key(destination, SOURCE_FILE), text)
    # configuration
    text = read_text(project_key(source, CONFIG_FILE))
    if text is not None:
        write_text(project_key(destination, CONFIG_FILE), text)

# --- LAST RUN STUFF ---
"""References to a PROJECT"""

def read_last_run(project: Project) -> dict | None:
    """Read the result of the project's last run, or None if it never ran"""
    return read_json(project_key(project, LAST_RUN_FILE))

# --- JOB STUFF ---
"""References to a JOB"""

def write_request(job_id: uuid.UUID, request: dict) -> None:
    """Write the request of a job"""
    write_text(job_key(job_id, REQUEST_FILE), json.dumps(request))

def write_last_run(project: Project, result: dict) -> None:
    """Save a run's result as the project's last run, with its full pipeline CSV if it has one"""
    pipeline = result["pipeline"]
    if pipeline.get("tooLarge"):
        # The CSV lives in jobs/, which is temporary so we keep a copy in last-run/
        csv_key = project_key(project, LAST_RUN_CSV_FILE)
        write_text(csv_key, read_text(pipeline["csvPath"]))
        
        result = copy.deepcopy(result)
        result["pipeline"]["csvPath"] = csv_key
        
    write_text(project_key(project, LAST_RUN_FILE), json.dumps(result))

def read_result(job: Job) -> dict | None:
    """Read the result of a finished job or None if it was already cleaned up"""
    return read_json(job.result_key)