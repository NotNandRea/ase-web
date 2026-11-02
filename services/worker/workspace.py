"""Job workspace: a private folder dedicated to the job that looks like the repository for the backend
The actual folder is created by worker.py, here we create the subfolders and symlinks inside it,
this file is just a utility for the worker

Inside the job folder we create:

    setup_default      symlink to the repository's file
    gem5/              symlink to the repository's folder
    programs/demo.mk   symlink to the repository's file
    programs/          the project will be created here by run_job.py
    results/           gem5 writes its output here

We use symlinks as the shared files stay in the repository, and every
job only gets its own programs/ and results/.
"""

from pathlib import Path

"""
This file is services/worker/workspace.py: three levels up is the repository.
We need REPO to create symlinks to the shared files
"""
REPO = Path(__file__).parent.parent.parent.absolute()

# Receives job folder path as string and populates it with the required structure
def create(job_dir):
    job_dir = Path(job_dir) 

    # The job's own folders.
    (job_dir / "programs").mkdir(parents=True)
    (job_dir / "results").mkdir()

    # Links to the shared parts of the repository.
    (job_dir / "setup_default").symlink_to(REPO / "setup_default")
    (job_dir / "gem5").symlink_to(REPO / "gem5")
    (job_dir / "programs" / "demo.mk").symlink_to(REPO / "programs" / "demo.mk")