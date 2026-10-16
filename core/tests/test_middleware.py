import json

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.middleware import IdempotencyMiddleware


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        value = self.values.get(key)
        if isinstance(value, str):
            return value.encode("utf-8")
        return value

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    def setex(self, key, ttl, value):
        self.values[key] = value.encode("utf-8") if isinstance(value, str) else value
        return True

    def eval(self, script, numkeys, key, token):
        stored = self.get(key)
        token_bytes = token.encode("utf-8") if isinstance(token, str) else token
        if stored == token_bytes:
            self.values.pop(key, None)
            return 1
        return 0


class IdempotencyMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.redis = FakeRedis()
        self.calls = 0

        def get_response(request):
            self.calls += 1
            return HttpResponse(
                json.dumps({"call": self.calls}),
                content_type="application/json",
                status=201,
            )

        self.middleware = IdempotencyMiddleware(get_response)
        self.middleware.redis_client = self.redis

    def make_request(self, body='{"title":"example"}', authorization="Bearer user-a"):
        request = self.factory.post(
            "/api/tasks/",
            data=body,
            content_type="application/json",
            HTTP_X_IDEMPOTENCY_KEY="request-123",
            HTTP_AUTHORIZATION=authorization,
        )
        return request

    def test_replays_successful_response_for_same_request(self):
        first = self.middleware(self.make_request())
        second = self.middleware(self.make_request())

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.content, second.content)
        self.assertEqual(second["X-Idempotency-Replayed"], "true")
        self.assertEqual(self.calls, 1)

    def test_rejects_reusing_key_with_different_body(self):
        self.middleware(self.make_request())
        response = self.middleware(self.make_request(body='{"title":"different"}'))

        self.assertEqual(response.status_code, 409)
        self.assertIn(b"different request", response.content)
        self.assertEqual(self.calls, 1)

    def test_scopes_cached_responses_to_authorization_identity(self):
        first = self.middleware(self.make_request(authorization="Bearer user-a"))
        second = self.middleware(self.make_request(authorization="Bearer user-b"))

        self.assertNotEqual(first.content, second.content)
        self.assertNotIn("X-Idempotency-Replayed", second.headers)
        self.assertEqual(self.calls, 2)

    def test_rejects_oversized_idempotency_key(self):
        request = self.factory.post(
            "/api/tasks/",
            data="{}",
            content_type="application/json",
            HTTP_X_IDEMPOTENCY_KEY="x" * 256,
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.calls, 0)
