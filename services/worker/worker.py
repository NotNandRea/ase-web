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

import workspace

PENDING = Path("/tmp/ase-queue/pending")
DONE = Path("/tmp/ase-queue/done")
RUN_JOB = Path(__file__).parent / "run_job.py"

TIMEOUT = 15   # maximum seconds to wait for a job to finish before killing it and returning an error


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

    try:
        # Wait for run_job.py, but never longer than TIMEOUT.
        subprocess.run([sys.executable, RUN_JOB, job_dir], timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        # subprocess.run has already killed run_job.py, but gem5 runs in its own
        # process group and survives it. Every process of this job has the job
        # folder in its command line, so we kill them all by that name.
        subprocess.run(["pkill", "-KILL", "-f", str(job_dir)])
        result = {"error": f"The simulation did not finish within {TIMEOUT} seconds.",
                  "status": 408}
    else:
        result_file = job_dir / "result.json"
        if result_file.exists():
            result = json.loads(result_file.read_text())
        else:
            result = {"error": "The job stopped without producing a result.", "status": 500}

    finally:
        shutil.rmtree(job_dir)
        
    return result


PENDING.mkdir(parents=True, exist_ok=True)
DONE.mkdir(parents=True, exist_ok=True)

# temporary stuff until implementing the real queue
while True:
    jobs = sorted(PENDING.glob("*.json"))
    if not jobs:
        time.sleep(1)   # nothing to do: sleep, then look again
        continue

    job_file = jobs[0]
    print("Running", job_file.stem)
    result = run(job_file)
    (DONE / job_file.name).write_text(json.dumps(result))
    job_file.unlink()
    print("Finished", job_file.stem)