"""S3 access: where project files live, and how to read and write them"""

import os
import uuid
import json

from models import Project

from ase_studio import backend

import boto3


BUCKET = os.environ["S3_BUCKET"]
s3 = boto3.client("s3")
SOURCE_FILE = "main.s"
CONFIG_FILE = ".ase-studio.json"
LAST_RUN_FILE = "last-run/result.json"

# --- S3 CORE FEATURES ---

def read_text(key: str) -> str | None:
    """Read a text file from S3, or None if it does not exist"""
    try:
        return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode()
    except s3.exceptions.NoSuchKey:
        return None


def write_text(key: str, text: str) -> None:
    """Write a text file to S3"""
    s3.put_object(Bucket=BUCKET, Key=key, Body=text.encode())
    
# --- KEY CREATION ---

def project_key(project: Project, filename: str) -> str:
    """S3 key of one file of a project"""
    return f"users/{project.owner}/projects/{project.id}/{filename}"

# --- SOURCE STUFF---

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
    """Save the project's CPU configuration, like the original project_config"""
    # indentation and newline are cosmetic, but make the file readable by humans ad the origilal backend
    write_text(project_key(project, CONFIG_FILE), json.dumps(config, indent=2) + "\n") 

# --- MISCELLANEOUS STUFF ---

def read_last_run(project: Project) -> dict | None:
    """Read the result of the project's last run, or None if it never ran"""
    text = read_text(project_key(project, LAST_RUN_FILE))
    if text is None:
        return None
    return json.loads(text)