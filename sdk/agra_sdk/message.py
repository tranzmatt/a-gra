from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Payload = dict[str, Any]


@dataclass(slots=True)
class AgraMessage:
    """A schema-rooted A-GRA/UCI XML message.

    `name` is the top-level XSD element name, for example `ActionCommand`.
    `payload` is a nested dictionary matching the XML child element structure.
    Attributes can be supplied for the top-level XML element through `attributes`.
    """

    name: str
    payload: Payload = field(default_factory=dict)
    attributes: dict[str, str] = field(default_factory=dict)

    def require(self, field_name: str) -> Any:
        if field_name not in self.payload:
            raise KeyError(f"{self.name} is missing required field {field_name!r}")
        return self.payload[field_name]
