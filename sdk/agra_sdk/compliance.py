from __future__ import annotations

from dataclasses import dataclass

from .message import AgraMessage
from .schema import SchemaRepository


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    index: int | None
    message: str


@dataclass(frozen=True, slots=True)
class SequenceExpectation:
    """Expected message flow for an ICD interaction."""

    message_names: tuple[str, ...]
    primitives: tuple[str, ...] = ()


class InteractionValidator:
    def __init__(self, schema: SchemaRepository | None = None) -> None:
        self.schema = schema or SchemaRepository.from_default_paths()

    def validate_message(self, message: AgraMessage) -> list[ValidationIssue]:
        return [
            ValidationIssue(None, issue)
            for issue in self.schema.validate_message_shape(message)
        ]

    def validate_sequence(
        self, messages: list[AgraMessage], expectation: SequenceExpectation
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        expected_names = expectation.message_names
        if len(messages) != len(expected_names):
            issues.append(
                ValidationIssue(
                    None,
                    f"Expected {len(expected_names)} messages, received {len(messages)}",
                )
            )
        for index, message in enumerate(messages):
            if index < len(expected_names) and message.name != expected_names[index]:
                issues.append(
                    ValidationIssue(
                        index,
                        f"Expected {expected_names[index]!r}, received {message.name!r}",
                    )
                )
            issues.extend(
                ValidationIssue(index, issue)
                for issue in self.schema.validate_message_shape(message)
            )
            if index < len(expectation.primitives):
                actual = self.schema.describe(message.name).primitive
                expected = expectation.primitives[index]
                if actual != expected:
                    issues.append(
                        ValidationIssue(
                            index,
                            f"Expected primitive {expected!r}, received {actual!r}",
                        )
                    )
        return issues
