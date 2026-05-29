from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable
from uuid import uuid4

from .message import AgraMessage
from .schema import SchemaRepository


class Primitive(StrEnum):
    DATA = "Data-1"
    DATA_RECORD = "DataRecord-1"
    STATUS = "Status-1"
    COMMAND = "Command-2"
    ACTION_REQUEST = "ActionRequest-2"
    DATA_REQUEST = "DataRequest-2"


class Interface(StrEnum):
    C2 = "C2"
    MISSION_DEBRIEF = "MD"
    MISSION_PLAN = "MP"
    MISSION_SYSTEMS = "MS"
    PEER = "P2P"
    VEHICLE = "VI"


@dataclass(slots=True)
class MessageEnvelope:
    message: AgraMessage
    source: str
    destination: str | None = None
    interface: Interface | str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


Handler = Callable[[MessageEnvelope], None]


class MessageBus:
    """In-memory pub/sub bus for implementing and testing ICD interactions."""

    def __init__(self, schema: SchemaRepository | None = None) -> None:
        self.schema = schema or SchemaRepository.from_default_paths()
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._primitive_subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, message_name: str, handler: Handler) -> None:
        self.schema.describe(message_name)
        self._subscribers[message_name].append(handler)

    def subscribe_primitive(self, primitive: Primitive | str, handler: Handler) -> None:
        self._primitive_subscribers[str(primitive)].append(handler)

    def publish(self, message: AgraMessage | MessageEnvelope) -> MessageEnvelope:
        envelope = (
            message
            if isinstance(message, MessageEnvelope)
            else MessageEnvelope(message=message, source="local")
        )
        definition = self.schema.describe(envelope.message.name)
        for handler in list(self._subscribers.get(envelope.message.name, [])):
            handler(envelope)
        if definition.primitive:
            for handler in list(self._primitive_subscribers.get(definition.primitive, [])):
                handler(envelope)
        return envelope


class CommandTracker:
    """Tracks `*Command` to `*CommandStatus` correlations by message family."""

    def __init__(self) -> None:
        self.pending: dict[str, MessageEnvelope] = {}
        self.statuses: dict[str, MessageEnvelope] = {}

    def submit(self, envelope: MessageEnvelope) -> str:
        self.pending[envelope.correlation_id] = envelope
        return envelope.correlation_id

    def accept_status(self, envelope: MessageEnvelope) -> str | None:
        if not envelope.message.name.endswith("CommandStatus"):
            return None
        correlation_id = envelope.correlation_id
        self.statuses[correlation_id] = envelope
        self.pending.pop(correlation_id, None)
        return correlation_id


class RequestTracker:
    """Tracks `*Request` to `*RequestStatus` correlations by envelope id."""

    def __init__(self) -> None:
        self.pending: dict[str, MessageEnvelope] = {}
        self.statuses: dict[str, MessageEnvelope] = {}

    def submit(self, envelope: MessageEnvelope) -> str:
        self.pending[envelope.correlation_id] = envelope
        return envelope.correlation_id

    def accept_status(self, envelope: MessageEnvelope) -> str | None:
        if not envelope.message.name.endswith("RequestStatus"):
            return None
        correlation_id = envelope.correlation_id
        self.statuses[correlation_id] = envelope
        self.pending.pop(correlation_id, None)
        return correlation_id
