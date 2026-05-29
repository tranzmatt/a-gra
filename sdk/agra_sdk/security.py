from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Classification(StrEnum):
    UNCLASSIFIED = "U"
    CONFIDENTIAL = "C"
    SECRET = "S"
    TOP_SECRET = "TS"


@dataclass(slots=True)
class SecurityInformation:
    """Helper for the `SecurityInformationType` structure in the markings XSD."""

    classification: str | Classification
    owner_producer: list[str] = field(default_factory=list)
    joint: bool | None = None
    releasable_to: list[str] = field(default_factory=list)
    dissemination_controls: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def unclassified(cls, owner_producer: str = "USA") -> "SecurityInformation":
        return cls(Classification.UNCLASSIFIED, [owner_producer])

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "Classification": str(self.classification),
            "OwnerProducer": [
                {"GovernmentIdentifier": value} for value in self.owner_producer
            ],
        }
        if self.joint is not None:
            payload["Joint"] = self.joint
        if self.dissemination_controls:
            payload["DisseminationControls"] = self.dissemination_controls
        if self.releasable_to:
            payload["ReleasableTo"] = [
                {"GovernmentIdentifier": value} for value in self.releasable_to
            ]
        payload.update(self.extra)
        return payload
