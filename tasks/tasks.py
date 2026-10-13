import logging

from celery import shared_task
from django.db import transaction

from .models import Task, TaskStatus


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def process_task(self, task_id: int):
    task = Task.objects.get(pk=task_id)

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

        # Replace this section with the actual business operation.
        result = {
            "message": "Task processed successfully",
            "task_id": task_id,
        }

        Task.objects.filter(pk=task_id).update(
            status=TaskStatus.COMPLETED,
            result_data=result,
            error_message="",
            retry_count=self.request.retries,
        )

        return result

    except Exception as exc:
        retry_number = self.request.retries + 1

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

        raise