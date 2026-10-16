from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tasks.models import Task, TaskStatus

User = get_user_model()


class TaskAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="task-owner",
            password="test-password-123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_task_persists_and_dispatches_after_commit(self):
        with patch("tasks.views.process_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/tasks/",
                    {"title": "Lifecycle test", "description": "Verify queueing"},
                    format="json",
                )

        self.assertEqual(response.status_code, 201)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.status, TaskStatus.PENDING)
        delay.assert_called_once_with(task.id)

    def test_user_only_sees_their_own_tasks(self):
        other_user = User.objects.create_user(
            username="another-owner",
            password="test-password-456",
        )
        own_task = Task.objects.create(owner=self.user, title="Mine")
        Task.objects.create(owner=other_user, title="Not mine")

        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(returned_ids, {own_task.id})
