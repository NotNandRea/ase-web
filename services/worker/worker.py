"""Worker takes a job from the queue, one at a time, and run it

JUST FOR TESTING BEFORE IMPLEMENTING A REAL QUEUE IN POSTGRES, HERE I USE DIRECTORIES
    /tmp/ase-queue/pending/<id>.json   jobs waiting to run (same content as job.json)
    /tmp/ase-queue/done/<id>.json      their results (same content as result.json)
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import boto3
import os

import jobs_dao
import workspace


RUN_JOB = Path(__file__).parent / "run_job.py"

REQUESTS = Path(tempfile.gettempdir()) / "ase-requests" # job requests downloaded from S3

TIMEOUT = 60   # maximum seconds to wait for a job to finish before killing it and returning an error
WAKEUP_TIMEOUT = 60   # look at the queue at least this often, even if no producer signals

BUCKET = os.environ["S3_BUCKET"]

s3 = boto3.client("s3")
db = jobs_dao.connect()


def run(job_file):
    # Run one job in its own folder and process, and return its result
    # name the folder as the job uuid (filename without extension)
    job_id = job_file.stem
    job_dir = Path(tempfile.gettempdir()) / f"ase-job-{job_id}" # create a folder inside /tmp for the job
    shutil.rmtree(job_dir, ignore_errors=True)   # remove any existing leftovers of an interrupted run of this job
    job_dir.mkdir()
    workspace.create(job_dir)
    # put the job.json inside the job folder
    shutil.copy(job_file, job_dir / "job.json")

    csv = None   # full pipeline CSV, only for programs too long to display

    try:
        # Wait for run_job.py, but never longer than TIMEOUT.
        subprocess.run([sys.executable, RUN_JOB, job_dir], timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        # subprocess.run has already killed run_job.py, but gem5 runs in its own
        # process group and survives it. Every process of this job has the job
        # folder in its command line, so we kill them all by that name.
        subprocess.run(["pkill", "-KILL", "-f", str(job_dir)])
        result = {"error": f"The simulation did not finish within {TIMEOUT} seconds.",
                  "status": 500}
    else:
        result_file = job_dir / "result.json"
        if result_file.exists():
            result = json.loads(result_file.read_text())
        else:
            result = {"error": "The job stopped without producing a result.", "status": 500}
        # Programs too long to display: the backend wrote the whole pipeline to a
        # CSV file inside the job folder (csvPath). Read it before the folder is deleted.
        pipeline = result.get("pipeline", {})
        if pipeline.get("tooLarge"):
            csv = Path(pipeline["csvPath"]).read_bytes()

    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        
    return result, csv


REQUESTS.mkdir(parents=True, exist_ok=True)

while True:
    # get a job
    job = jobs_dao.claim_job(db)
    if job is None:
        jobs_dao.wait_for_jobs(db, WAKEUP_TIMEOUT)
        continue
    
    job_id, request_key = job
    print(f"Worker: running job {job_id} (request {request_key})")
    
    # Download the job request from S3
    job_file = REQUESTS / f"{job_id}.json" # path to the job request file in /tmp/ase-requests
    s3.download_file(Bucket=BUCKET, Key=request_key, Filename=str(job_file))
    
    result, csv = run(job_file)
    
    # Programs too long to display: upload the full pipeline CSV next to the result,
    # and make csvPath point to it on S3 instead of the worker's disk.
    if csv is not None:
        csv_key = f"jobs/{job_id}/pipeline-full.csv"
        s3.put_object(Bucket=BUCKET, Key=csv_key, Body=csv)
        result["pipeline"]["csvPath"] = csv_key
    
    # Upload the result to S3
    result_key = f"jobs/{job_id}/result.json" # key of the result file in S3
    s3.put_object(Bucket=BUCKET, Key=result_key, Body=json.dumps(result).encode())
    
    job_file.unlink() # remove the job request file from /tmp/ase-requests
    jobs_dao.finish_job(db, job_id, result_key)