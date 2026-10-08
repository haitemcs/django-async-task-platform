import json
import redis
from django.conf import settings
from django.http import HttpResponse


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        self.redis_client = redis.Redis.from_url(broker_url)

    def __call__(self, request):
        if request.method not in ["POST", "PUT", "PATCH"]:
            return self.get_response(request)

        idempotency_key = request.headers.get("X-Idempotency-Key") or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
        if not idempotency_key:
            return self.get_response(request)

        cache_key = f"idempotency:{idempotency_key}"

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                payload = json.loads(cached_data.decode("utf-8"))
                response = HttpResponse(
                    content=payload["content"],
                    status=payload["status"],
                    content_type=payload["content_type"],
                )
                response["X-Cache-Hit"] = "true"
                return response
        except Exception:
            pass

        response = self.get_response(request)

        if 200 <= response.status_code < 300:
            try:
                payload = {
                    "status": response.status_code,
                    "content": response.content.decode("utf-8"),
                    "content_type": response.get("Content-Type", "application/json"),
                }
                self.redis_client.setex(cache_key, 86400, json.dumps(payload))
            except Exception:
                pass

        return response
