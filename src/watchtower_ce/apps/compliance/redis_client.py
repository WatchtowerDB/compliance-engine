import redis
from django.conf import settings

# A single ConnectionPool shared across the entire process.
# Both the Celery worker process and the Django/WSGI process will each
# create their own pool (one per process).
#
# redis-py's ConnectionPool is thread-safe, so a single pool instance is
# fine for concurrent Django requests and concurrent Celery task threads.
_pool = redis.ConnectionPool.from_url(
    settings.CELERY_BROKER_URL,
    decode_responses=False,  # keep bytes; callers decode explicitly where needed
    max_connections=20,
)


def get_redis() -> redis.Redis:
    """
    Return a Redis client backed by the shared pool.

    Calling this repeatedly is cheap; redis-py reuses connections from the
    pool rather than opening new sockets each time.
    """
    return redis.Redis(connection_pool=_pool)
