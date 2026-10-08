import time
from celery import shared_task


@shared_task
def process_background_job(job_id):
    time.sleep(2)
    return f"Job {job_id} processed successfully"
