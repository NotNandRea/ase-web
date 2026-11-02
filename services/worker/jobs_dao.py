"""The table is the QUEUE between producers and consumers (the workers)
Inspired by the producer-consumer well-known problem:

    INSERT + NOTIFY jobs   enqueue + signal(full)   done by the producer
    claim_job()            dequeue                  SKIP LOCKED is the mutex between workers
    wait_for_jobs()        wait(full)               LISTEN: sleep until a producer signals

Not like a semaphore, a notification is not counted and is lost if nobody listens it
"""

import os

import psycopg

CHANNEL = "jobs"   # producers send NOTIFY on this channel after inserting a job

# Take the oldest pending job, mark it as running, and return its id and request key.
# FOR UPDATE SKIP LOCKED: if another worker is taking the same row in the same moment, skip it.
CLAIM_JOB = """
    UPDATE jobs
    SET status = 'running', started_at = now()
    WHERE id = (
        SELECT id FROM jobs
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id, request_key
"""

# Mark the job as done
# status ='running' is for future purposes, to avoid marking a job as done if it was already marked as failed by the clenup process
FINISH_JOB = """
    UPDATE jobs SET status = 'done', result_key = %s
    WHERE id = %s AND status = 'running'
"""


def connect():
    """Open the worker's database connection and start listening for new jobs."""
    db = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) # commit automatically after each statement
    db.execute(f"LISTEN {CHANNEL}") # listen for notifications from producers, so we can wake up when a new job is inserted
    return db


def claim_job(db):
    """Take the oldest pending job. Return (job_id, request_key), or None if the queue is empty."""
    return db.execute(CLAIM_JOB).fetchone()


def finish_job(db, job_id, result_key):
    """Mark the job as done with its result, only if it is still running."""
    db.execute(FINISH_JOB, (result_key, job_id))


def wait_for_jobs(db, timeout):
    """Sleep until a producer announces a new job, or at most `timeout` seconds.
    In this case next() is necessary because notifies() is a generator adn we
    need to consume it to actually wait for the notification.
    """
    # notifies() blocks until: 1. a producer sends a NOTIFY (stop_after=1) 2. the timeout expires
    next(db.notifies(timeout=timeout, stop_after=1), None)   