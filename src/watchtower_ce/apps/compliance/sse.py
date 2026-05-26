import datetime
import json
import uuid
from typing import Generator, cast

from .redis_client import get_redis


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def build_cloud_event(
    event_type: str,
    source: str,
    data: dict,
    subject: str | None = None,
    event_id: str | None = None,
) -> dict:
    """
    Build a spec-compliant CloudEvent (v1.0) dict.

    Required attributes per spec: specversion, id, source, type.
    Optional included: time, datacontenttype, subject.

    Args:
        event_type (str): The type of event (e.g., "com.watchtower.compliance.phase.update").
            Follows reverse-domain name notation for uniqueness.
        source (str): URI or name identifying the context that originated the event.
            Typically a service name, endpoint, or component identifier.
        data (dict): The event payload data. Will be serialized as JSON in the final event.
        subject (str | None): Optional subject of the event (e.g., a specific resource ID
            like a scan session or user ID). Defaults to None.
        event_id (str | None): Optional unique event identifier. If not provided,
            a UUID v4 will be generated automatically.

    Returns:
        dict: the built CloudEvent ready for serialization and transmission
    """
    event = {
        "specversion": "1.0",
        "id": event_id or str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "time": _now_iso(),
        "datacontenttype": "application/json",
        "data": data,
    }
    if subject:
        event["subject"] = subject
    return event


def format_sse(event_id: str | None, cloud_event: dict) -> str:
    """
    Serialize a CloudEvent dict to an SSE frame.

    The SSE `event:` field mirrors the CloudEvent `type` so consumers can
    filter on either layer consistently.

    Args:
        event_id (str | None): Unique identifier for this SSE message. Used as the SSE `id:` field.
            For replay events, this should be the Redis stream entry ID. For other events, this
            field should ideally be set to `None` (so no ID will be set) as to not overwrite the
            `last-event-id` header value that the frontend relies on for reconnection.
        cloud_event (dict): A CloudEvent dict (as produced by `build_cloud_event()`)
            containing the event data, type, and metadata to be sent as the SSE `data:` field.

    Returns:
        str: A properly formatted SSE message string with event, id, and data fields,
            ending with two newlines as required by SSE protocol.
    """
    lines = f"event: {cloud_event['type']}\n"
    if event_id is not None:
        lines += f"id: {event_id}\n"
    lines += f"data: {json.dumps(cloud_event)}\n\n"
    return lines


class RedisSSEStream:
    """
    Wraps a Redis Stream (XADD/XRANGE/XREAD) to give SSE endpoints
    durable, replayable event history keyed by stream entry IDs.

    All events emitted — including system events — are spec-compliant
    CloudEvents serialised as JSON in the SSE `data:` field.
    The SSE `event:` field always mirrors the CloudEvent `type`.

    Consuming side: instantiate and call .stream(last_event_id).
    Streaming side: handled exclusively by stream_event() in tasks.py.
    """

    BLOCK_MS = 5_000  # how long XREAD blocks waiting for new messages
    STREAM_TTL = 900  # expire the Redis stream key after 15 minutes

    # System event types
    EVT_CONNECTED = "com.watchtower.system.connected"
    EVT_RESUMING = "com.watchtower.system.resuming"
    EVT_COMPLETED = "com.watchtower.system.completed"

    def __init__(self, channel: str) -> None:
        """
        Initialize a RedisSSEStream instance.

        Args:
            channel (str): The Redis stream channel/key name to read events from.
                This should match the channel used by the streaming side.
        """
        self.channel = channel
        self._redis = get_redis()

    def _system_event(self, event_type: str, data: dict) -> dict:
        """
        Create a system CloudEvent with the /system/sse source.

        Args:
            event_type (str): System event type (e.g., EVT_CONNECTED, EVT_RESUMING)
            data (dict): Event payload data

        Returns:
            dict: A complete CloudEvent dict ready for serialization
        """
        return build_cloud_event(
            event_type=event_type,
            source="/system/sse",
            data=data,
        )

    def _is_terminal(self, cloud_event: dict) -> bool:
        """
        Return True if this event should close the stream.

        Terminal events include:
        - compliance phase updates with step="analysis" and status="completed"
        - compliance phase updates with step="model_initialization" and
          status="completed" or "partial"

        Args:
            cloud_event (dict): A CloudEvent dict to evaluate

        Returns:
            bool: True if this event indicates the stream should terminate,
                False otherwise
        """
        event_type = cloud_event.get("type", "")
        data = cloud_event.get("data", {})

        if event_type == "com.watchtower.compliance.phase.update":
            if data.get("step") == "analysis" and data.get("status") == "completed":
                return True
            if data.get("step") == "model_initialization" and data.get("status") in {
                "completed",
                "partial",
            }:
                return True

        return False

    def _find_latest_phase(self, last_event_id: str) -> dict | None:
        """
        Scan all events up to and including last_event_id to find
        the most recent phase.update payload, if any.

        Used during reconnection to determine the last known state
        that should be reported to the client.

        Args:
            last_event_id (str): The last event ID the client has received.
                Redis stream ID format (e.g., "1234567890-0").

        Returns:
            dict | None: The most recent phase.update payload (the `data` field
                from the CloudEvent), or None if no phase.update events exist
                in the scanned range.
        """
        entries = cast(
            list[tuple[bytes, dict[bytes, bytes]]],
            self._redis.xrange(self.channel, min="-", max=last_event_id),
        )
        latest_phase: dict | None = None

        for _, fields in entries:
            try:
                payload = json.loads(fields[b"data"].decode())
                if payload.get("type") == "com.watchtower.compliance.phase.update":
                    latest_phase = payload.get("data", {})
            except (json.JSONDecodeError, KeyError):
                continue

        return latest_phase

    def stream(self, last_event_id: str | None = None) -> Generator[str, None, None]:
        """
        Generator that yields SSE-formatted strings.

        Workflow:
        1. Emits a `com.watchtower.system.connected` event immediately.
        2. On reconnect (if last_event_id provided): scans the backlog up to last_event_id
           to find the last known phase, then emits a `com.watchtower.system.resuming`
           event with the discovered state.
        3. Replays any events that occurred after last_event_id from the Redis stream.
        4. Tails the stream live using XREAD with blocking, yielding new events as they arrive.
        5. Sends SSE keepalive comments (`: keepalive`) on idle polls to prevent connection timeouts.
        6. Terminates the generator when a terminal event is encountered.

        Args:
            last_event_id (str | None): The last event ID the client has successfully
                received. Used for resuming interrupted connections. Can be:
                - None: New connection, start from beginning
                - "0-0": Start from beginning (equivalent to None)
                - Specific ID: Resume from after this event
                - "$": Start live tail only (no replay)

        Yields:
            str: SSE-formatted strings ready to be written to an HTTP response.
                These include both system events and regular CloudEvents.
        """
        yield format_sse(
            None,
            self._system_event(self.EVT_CONNECTED, {"status": "connected"}),
        )

        cursor = last_event_id or "0-0"

        # ── On reconnect: find last known phase and emit resuming hint ──────── #
        if last_event_id:
            latest_phase = self._find_latest_phase(last_event_id)

            if latest_phase:
                yield format_sse(
                    None,
                    self._system_event(
                        self.EVT_RESUMING,
                        {
                            "last_known_step": latest_phase.get("step"),
                            "last_known_status": latest_phase.get("status"),
                        },
                    ),
                )

        # ── Replay backlog ───────────────────────────────────────────────────── #
        start = f"({cursor}" if last_event_id else "-"
        backlog = cast(
            list[tuple[bytes, dict[bytes, bytes]]],
            self._redis.xrange(self.channel, min=start, max="+"),
        )

        for entry_id_bytes, fields in backlog:
            entry_id = entry_id_bytes.decode()
            cursor = entry_id
            raw = fields[b"data"].decode()
            try:
                cloud_event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            yield format_sse(entry_id, cloud_event)
            if self._is_terminal(cloud_event):
                return

        # ── Live tail ────────────────────────────────────────────────────────── #
        if cursor == "0-0":
            cursor = "$"

        while True:
            results = cast(
                list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]],
                self._redis.xread(
                    {self.channel: cursor}, block=self.BLOCK_MS, count=10
                ),
            )
            if not results:
                yield ": keepalive\n\n"  # SSE comment, not a CloudEvent
                continue

            for _stream, entries in results:
                for entry_id_bytes, fields in entries:
                    cursor = entry_id_bytes.decode()
                    raw = fields[b"data"].decode()
                    try:
                        cloud_event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    yield format_sse(cursor, cloud_event)
                    if self._is_terminal(cloud_event):
                        return
