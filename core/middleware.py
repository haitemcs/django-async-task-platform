import hashlib
import json
import logging
import uuid

import redis
from django.conf import settings
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# Only the process that created a lock may release it.
_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


class IdempotencyMiddleware:
    """
    Best-effort response idempotency for successful write requests.

    Keys are scoped by request method/path, the supplied idempotency key, and
    a hash of the caller's authorization/session credentials. The request
    fingerprint prevents accidentally reusing a key for a different payload.

    Redis failures deliberately fail open so the API remains available; in
    that situation, idempotency cannot be guaranteed for that request.
    """

    cache_ttl_seconds = 86400
    lock_ttl_seconds = 60
    max_key_length = 255

    def __init__(self, get_response):
        self.get_response = get_response
        redis_url = getattr(
            settings,
            "REDIS_URL",
            getattr(
                settings,
                "CELERY_BROKER_URL",
                "redis://127.0.0.1:6379/0",
            ),
        )
        self.redis_client = redis.Redis.from_url(redis_url, socket_timeout=1)

    @staticmethod
    def _digest(value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def _conflict(message: str) -> JsonResponse:
        return JsonResponse({"detail": message}, status=409)

    def _scope(self, request, idempotency_key: str) -> str:
        # Do not store raw credentials or client-supplied keys in Redis keys.
        identity = "\\0".join(
            (
                request.headers.get("Authorization", ""),
                request.COOKIES.get("sessionid", ""),
            )
        )
        scope = "\\0".join(
            (
                request.method,
                request.get_full_path(),
                idempotency_key,
                self._digest(identity.encode("utf-8")),
            )
        )
        return self._digest(scope.encode("utf-8"))

    def _replay(self, cached_data: bytes, request_fingerprint: str):
        try:
            payload = json.loads(cached_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None

        if payload.get("request_fingerprint") != request_fingerprint:
            return self._conflict(
                "This idempotency key was already used with a different request."
            )

        response = HttpResponse(
            content=payload["content"],
            status=payload["status"],
            content_type=payload.get("content_type", "application/json"),
        )
        for name, value in payload.get("headers", {}).items():
            response[name] = value
        response["X-Idempotency-Replayed"] = "true"
        return response

    def __call__(self, request):
        if request.method not in {"POST", "PUT", "PATCH"}:
            return self.get_response(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return self.get_response(request)

        if len(idempotency_key) > self.max_key_length:
            return JsonResponse(
                {"detail": "X-Idempotency-Key must be 255 characters or fewer."},
                status=400,
            )

        body = request.body
        request_fingerprint = self._digest(
            b"\\0".join(
                (
                    request.method.encode("utf-8"),
                    request.get_full_path().encode("utf-8"),
                    request.content_type.encode("utf-8")
                    if request.content_type
                    else b"",
                    body,
                )
            )
        )
        scope_hash = self._scope(request, idempotency_key)
        cache_key = f"idempotency:response:{scope_hash}"
        lock_key = f"idempotency:lock:{scope_hash}"
        lock_token = uuid.uuid4().hex

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data is not None:
                replay = self._replay(cached_data, request_fingerprint)
                if replay is not None:
                    return replay

            acquired = self.redis_client.set(
                lock_key,
                lock_token,
                nx=True,
                ex=self.lock_ttl_seconds,
            )
            if not acquired:
                # The first request may have completed between the initial
                # cache lookup and the lock attempt.
                cached_data = self.redis_client.get(cache_key)
                if cached_data is not None:
                    replay = self._replay(cached_data, request_fingerprint)
                    if replay is not None:
                        return replay
                response = self._conflict(
                    "A request with this idempotency key is already in progress. Retry shortly."
                )
                response["Retry-After"] = "1"
                return response
        except redis.RedisError:
            logger.warning(
                "Redis unavailable; processing request without idempotency protection",
                exc_info=True,
            )
            return self.get_response(request)

        try:
            response = self.get_response(request)
            if 200 <= response.status_code < 300 and not response.streaming:
                try:
                    content = response.content.decode("utf-8")
                    excluded_headers = {
                        "connection",
                        "content-length",
                        "date",
                        "server",
                        "set-cookie",
                        "transfer-encoding",
                    }
                    payload = {
                        "request_fingerprint": request_fingerprint,
                        "status": response.status_code,
                        "content": content,
                        "content_type": response.get(
                            "Content-Type", "application/json"
                        ),
                        "headers": {
                            name: value
                            for name, value in response.items()
                            if name.lower() not in excluded_headers
                        },
                    }
                    self.redis_client.setex(
                        cache_key,
                        self.cache_ttl_seconds,
                        json.dumps(payload),
                    )
                except (UnicodeDecodeError, TypeError, ValueError):
                    # Binary or non-serializable responses are not cached.
                    logger.debug("Skipping idempotency cache for non-text response")
                except redis.RedisError:
                    logger.warning(
                        "Could not cache idempotent response",
                        exc_info=True,
                    )
            return response
        finally:
            try:
                self.redis_client.eval(
                    _RELEASE_LOCK_SCRIPT,
                    1,
                    lock_key,
                    lock_token,
                )
            except redis.RedisError:
                logger.warning("Could not release idempotency lock", exc_info=True)
