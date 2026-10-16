from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from core.health import liveness_check, readiness_check


class HealthCheckTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_liveness_endpoint_returns_ok(self):
        response = liveness_check(self.factory.get("/health/live/"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": "live", "service": "async-task-platform"},
        )

    @patch("core.health.redis.Redis.from_url")
    @patch("core.health.connection.ensure_connection")
    def test_readiness_returns_200_when_dependencies_are_healthy(
        self, ensure_connection, redis_from_url
    ):
        redis_client = Mock()
        redis_client.ping.return_value = True
        redis_from_url.return_value = redis_client

        response = readiness_check(self.factory.get("/health/ready/"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "status": "ready",
                "checks": {
                    "database": "healthy",
                    "cache_redis": "healthy",
                },
            },
        )
        ensure_connection.assert_called_once()
        redis_client.ping.assert_called_once()

    @patch("core.health.redis.Redis.from_url")
    @patch(
        "core.health.connection.ensure_connection",
        side_effect=RuntimeError("sensitive database connection detail"),
    )
    def test_readiness_returns_503_without_exposing_exception_details(
        self, ensure_connection, redis_from_url
    ):
        redis_client = Mock()
        redis_client.ping.return_value = True
        redis_from_url.return_value = redis_client

        response = readiness_check(self.factory.get("/health/ready/"))

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content,
            {
                "status": "unhealthy",
                "checks": {
                    "database": "unhealthy",
                    "cache_redis": "healthy",
                },
            },
        )
        self.assertNotIn(b"sensitive database connection detail", response.content)
