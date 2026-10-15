import logging

from celery import shared_task
from django.db import transaction

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,                  # bind=True gives us 'self' so we can check how many times this task has failed and retried.
    autoretry_for=(Exception,), # If any error happens, Celery will automatically catch it and try again.
    retry_backoff=True,         # Spreads out retries over time so we don't hammer the server (1s, 2s, 4s...).
    retry_backoff_max=60,       # Caps the maximum wait time between retries at 60 seconds.
    max_retries=3,              # Gives it 3 tries total before giving up permanently.
)
def process_Task(self, task_id: int):
    # First, make sure the task actually exists in the database.
    task = Task.objects.get(pk=task_id)

    # Flip the status to PROCESSING immediately so the user knows work has started.
    Task.objects.filter(pk=task_id).update(
        status=TaskStatus.PROCESSING,
        error_message="",
    )

    try:
        logger.info(
            "Processing task_id=%s retry=%s",
            task_id,
            self.request.retries,
        )

        # --- Put your actual heavy work here (API calls, image processing, etc.) ---
        result = {
            "message": "Task processed successfully",
            "task_id": task_id,
        }
        # -----------------------------------------------------------------------

        # If we got here without errors, update the database to COMPLETED and save the result data.
        Task.objects.filter(pk=task_id).update(
            status=TaskStatus.COMPLETED,
            result_data=result,
            error_message="",
            retry_count=self.request.retries,
        )

        return result

    except Exception as exc:
        # Figure out what retry number we are on now.
        retry_number = self.request.retries + 1

        # If we maxed out our attempts, mark it permanently FAILED. 
        # Otherwise, flip it back to PENDING so Celery picks it up again after the backoff delay.
        if self.request.retries >= self.max_retries:
            Task.objects.filter(pk=task_id).update(
                status=TaskStatus.FAILED,
                error_message=str(exc),
                retry_count=retry_number,
            )
        else:
            Task.objects.filter(pk=task_id).update(
                status=TaskStatus.PENDING,
                error_message=str(exc),
                retry_count=retry_number,
            )

        logger.exception(
            "Task processing failed task_id=%s retry=%s",
            task_id,
            retry_number,
        )

        # IMPORTANT: You must re-raise the exception here! 
        # If you don't raise it, Celery won't know it failed and won't trigger the automatic retry.
        raise