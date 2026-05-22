import datetime
import json
from typing import Generator, cast

from .redis_client import get_redis


class RedisSSEStream:
    """
    Wraps a Redis Stream (XADD/XRANGE/XREAD) to give SSE endpoints
    durable, replayable event history keyed by stream entry IDs.

    Consuming side: instantiate and call .stream(last_event_id)
    Publishing side: handled exclusively by publish_event() in tasks.py.
    """

    BLOCK_MS = 5_000  # how long XREAD blocks waiting for new messages
    STREAM_TTL = 3_600  # expire the Redis stream key after 1 hour

    def __init__(self, channel: str) -> None:
        self.channel = channel
        self._redis = get_redis()

    def _make_sse_event(self, entry_id: str, data: str) -> str:
        # Extract the type from the JSON string so we can put it in the 'event:' header
        try:
            payload = json.loads(data)
            event_type = payload.get("type", "message")
        except json.JSONDecodeError:
            event_type = "message"

        return f"event: {event_type}\nid: {entry_id}\ndata: {data}\n\n"

    def _make_system_event(self, event_type: str, entry_id: str, payload: dict) -> str:
        return f"event: {event_type}\nid: {entry_id}\ndata: {json.dumps(payload)}\n\n"

    def _now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _is_terminal(self, data: str) -> bool:
        """Return True if this event should close the stream."""
        try:
            payload = json.loads(data)
            event_data = payload.get("data", {})

            if payload.get("type") == "com.watchtower.compliance.phase.update":
                # Compliance pipeline terminal: final analysis phase completion
                if (
                    event_data.get("step") == "analysis"
                    and event_data.get("status") == "completed"
                ):
                    return True

                # Model init terminal: completed (all ok) or partial (some frameworks failed)
                if event_data.get("step") == "model_initialization" and event_data.get(
                    "status"
                ) in {"completed", "partial"}:
                    return True

        except (json.JSONDecodeError, AttributeError):
            pass
        return False

    def stream(self, last_event_id: str | None = None) -> Generator[str, None, None]:
        """
        Generator that yields SSE-formatted strings.

        1. Emits a connection confirmation event.
        2. Replays any events after *last_event_id* from the Redis stream.
        3. Tails the stream live, yielding new events as they arrive.
        """
        yield self._make_system_event(
            "com.watchtower.system.connection",
            "init-1",
            {
                "specversion": "1.0",
                "source": "/system/sse",
                "time": self._now_iso(),
                "data": {"status": "connected"},
            },
        )

        # Initialize cursor. "0-0" means "from the start of the stream"
        cursor = last_event_id or "0-0"

        # ------------------------------ replay backlog ------------------------------ #
        # Note: we use "(" to make it exclusive if we have an ID
        start = f"({cursor}" if last_event_id else "-"
        backlog = cast(
            list[tuple[bytes, dict[bytes, bytes]]],
            self._redis.xrange(self.channel, min=start, max="+"),
        )

        for entry_id_bytes, fields in backlog:
            entry_id = entry_id_bytes.decode()
            cursor = entry_id  # Update cursor as we go
            yield self._make_sse_event(entry_id, fields[b"data"].decode())
            if self._is_terminal(fields[b"data"].decode()):
                return

        # --------------------------------- live tail -------------------------------- #
        if cursor == "0-0":
            cursor = "$"

        while True:
            results = self._redis.xread(
                {self.channel: cursor}, block=self.BLOCK_MS, count=10
            )
            if not results:
                yield "event: com.watchtower.system.keepalive\ndata: {}\n\n"
                continue

            for _stream, entries in results:
                for entry_id_bytes, fields in entries:
                    cursor = entry_id_bytes.decode()  # Always advance cursor
                    data = fields[b"data"].decode()
                    yield self._make_sse_event(cursor, data)
                    if self._is_terminal(data):
                        return
