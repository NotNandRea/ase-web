"""Run one job, in a temporary folder, and write its result to a file,
the job is executed in a separate process for job in order to garantee
a clean environment for every job

Usage:
    python3 run_job.py <job_dir>

Reads  <job_dir>/job.json     {"name", "text", "config", "allowScaffoldEdit"}
Writes <job_dir>/result.json  the result of the adapter, or an error
"""

import json
import os
import sys
import traceback

# get the job folder from the command line
job_dir = sys.argv[1]

# The backend decides its working folder when it is imported, by reading
# ASE_STUDIO_HOST_ROOT. So we set it first, and import the adapter after.
os.environ["ASE_STUDIO_HOST_ROOT"] = job_dir
import adapter

# read the job
with open(job_dir + "/job.json") as f:
    job = json.load(f)

try:
    # Same as creating a project in ASE Studio, then pressing Run.
    # sets up the project folder and runs the simulation
    result = adapter.create_project(job["name"])
    if "error" not in result:
        result = adapter.run(job["name"], job["text"], job["config"],
                             job["allowScaffoldEdit"])
except Exception as error:
    # same as the final exception in Handler in backend
    result = {"error": str(error), "status": 500}

# Write the result to a file, so worker.py can read it and send it back to the client.
with open(job_dir + "/result.json", "w") as f:
    json.dump(result, f)