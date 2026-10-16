from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from tasks.models import Task, TaskStatus
from tasks.tasks import process_task

User = get_user_model()


class ProcessTaskLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="worker-owner",
            password="test-password-789",
        )
        self.task = Task.objects.create(
            owner=self.user,
            title="Process me",
        )

    def test_successful_task_moves_to_completed_and_saves_result(self):
        result = process_task.apply(args=(self.task.id,), throw=True).get()
        self.task.refresh_from_db()

        self.assertEqual(self.task.status, TaskStatus.COMPLETED)
        self.assertEqual(self.task.result_data, result)
        self.assertEqual(result["task_id"], self.task.id)
        self.assertEqual(self.task.retry_count, 0)
        self.assertEqual(self.task.error_message, "")

    def test_repeated_processing_errors_eventually_mark_task_failed(self):
        with patch(
            "tasks.tasks._perform_task",
            side_effect=RuntimeError("simulated processing failure"),
        ):
            result = process_task.apply(args=(self.task.id,), throw=False)

        self.task.refresh_from_db()

        self.assertTrue(result.failed())
        self.assertEqual(self.task.status, TaskStatus.FAILED)
        self.assertEqual(self.task.retry_count, 4)
        self.assertIn("simulated processing failure", self.task.error_message)
