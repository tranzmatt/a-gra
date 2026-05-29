from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from .message import AgraMessage

XS = "http://www.w3.org/2001/XMLSchema"
UCI = "https://www.vdl.afrl.af.mil/programs/oam"
NS = {"xs": XS, "uci": UCI}


def _local_name(value: str) -> str:
    if value.startswith("{"):
        return value.rsplit("}", 1)[-1]
    if ":" in value:
        return value.split(":", 1)[1]
    return value


def _clean_docs(node: ET.Element) -> list[str]:
    docs: list[str] = []
    for doc in node.findall("xs:annotation/xs:documentation", NS):
        text = " ".join("".join(doc.itertext()).split())
        if text:
            docs.append(text)
    return docs


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    name: str
    type_name: str | None
    min_occurs: int = 1
    max_occurs: int | None = 1
    documentation: tuple[str, ...] = ()

    @property
    def required(self) -> bool:
        return self.min_occurs > 0

    @property
    def repeated(self) -> bool:
        return self.max_occurs is None or self.max_occurs > 1


@dataclass(frozen=True, slots=True)
class TypeDefinition:
    name: str
    fields: tuple[FieldDefinition, ...] = ()
    enum_values: tuple[str, ...] = ()
    documentation: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MessageDefinition:
    name: str
    type_name: str
    version: str | None
    primitive: str | None
    documentation: tuple[str, ...] = ()


@dataclass(slots=True)
class SchemaRepository:
    """Schema registry and XML codec for the A-GRA XSD set."""

    namespace: str = UCI
    messages: dict[str, MessageDefinition] = field(default_factory=dict)
    types: dict[str, TypeDefinition] = field(default_factory=dict)
    source_paths: tuple[Path, ...] = ()

    @classmethod
    def from_default_paths(cls, repo_root: str | Path | None = None) -> "SchemaRepository":
        root = cls._find_repo_root(
            Path(repo_root).resolve() if repo_root else Path(__file__).resolve()
        )
        return cls.from_paths(
            [
                root / "Schema" / "A-GRA_SecurityMarkings_v5_0_a.xsd",
                root / "Schema" / "A-GRA_MessageDefinitions_v5_0_a.xsd",
            ]
        )

    @staticmethod
    def _find_repo_root(start: Path) -> Path:
        candidates = [start if start.is_dir() else start.parent, *start.parents]
        for candidate in candidates:
            if (candidate / "Schema").is_dir():
                return candidate
        raise FileNotFoundError(
            f"Could not find A-GRA Schema directory starting at {start}"
        )

    @classmethod
    def from_paths(cls, paths: Iterable[str | Path]) -> "SchemaRepository":
        repo = cls(source_paths=tuple(Path(path) for path in paths))
        for path in repo.source_paths:
            repo._load_xsd(path)
        return repo

    def describe(self, message_name: str) -> MessageDefinition:
        try:
            return self.messages[message_name]
        except KeyError as exc:
            raise KeyError(f"Unknown A-GRA message {message_name!r}") from exc

    def type_for_message(self, message_name: str) -> TypeDefinition | None:
        message = self.describe(message_name)
        return self.types.get(message.type_name)

    def messages_by_primitive(self, primitive: str) -> list[MessageDefinition]:
        return sorted(
            (item for item in self.messages.values() if item.primitive == primitive),
            key=lambda item: item.name,
        )

    def enum_values(self, type_name: str) -> tuple[str, ...]:
        type_def = self.types.get(_local_name(type_name))
        if not type_def:
            raise KeyError(f"Unknown schema type {type_name!r}")
        return type_def.enum_values

    def validate_message_shape(self, message: AgraMessage) -> list[str]:
        issues: list[str] = []
        definition = self.messages.get(message.name)
        if not definition:
            return [f"Unknown message {message.name!r}"]
        type_def = self.types.get(definition.type_name)
        if not type_def:
            return issues
        for field_def in type_def.fields:
            if field_def.required and field_def.name not in message.payload:
                issues.append(
                    f"{message.name} missing required field {field_def.name!r}"
                )
        return issues

    def to_xml(self, message: AgraMessage, *, xml_declaration: bool = False) -> str:
        self.describe(message.name)
        ET.register_namespace("", self.namespace)
        root = ET.Element(f"{{{self.namespace}}}{message.name}", message.attributes)
        self._append_payload(root, message.payload)
        xml = ET.tostring(root, encoding="unicode", short_empty_elements=True)
        if xml_declaration:
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
        return xml

    def from_xml(self, xml_text: str | bytes) -> AgraMessage:
        root = ET.fromstring(xml_text)
        name = _local_name(root.tag)
        self.describe(name)
        return AgraMessage(
            name=name,
            payload=self._element_to_payload(root),
            attributes={_local_name(key): value for key, value in root.attrib.items()},
        )

    def _load_xsd(self, path: Path) -> None:
        tree = ET.parse(path)
        root = tree.getroot()
        for node in root.findall("xs:simpleType", NS):
            name = node.get("name")
            if not name:
                continue
            enums = tuple(
                value
                for enum in node.findall(".//xs:enumeration", NS)
                if (value := enum.get("value")) is not None
            )
            self.types[name] = TypeDefinition(
                name=name,
                enum_values=enums,
                documentation=tuple(_clean_docs(node)),
            )
        for node in root.findall("xs:complexType", NS):
            name = node.get("name")
            if not name:
                continue
            self.types[name] = TypeDefinition(
                name=name,
                fields=tuple(self._read_fields(node)),
                documentation=tuple(_clean_docs(node)),
            )
        for node in root.findall("xs:element", NS):
            name = node.get("name")
            type_name = node.get("type")
            if not name or not type_name:
                continue
            docs = tuple(_clean_docs(node))
            primitive = next(
                (
                    doc.split("UCI_PRIMITIVE:", 1)[1].strip().rstrip(".")
                    for doc in docs
                    if "UCI_PRIMITIVE:" in doc
                ),
                None,
            )
            self.messages[name] = MessageDefinition(
                name=name,
                type_name=_local_name(type_name),
                version=node.get(f"{{{UCI}}}version"),
                primitive=primitive,
                documentation=docs,
            )

    def _read_fields(self, node: ET.Element) -> list[FieldDefinition]:
        fields: list[FieldDefinition] = []
        for element in node.findall(".//xs:element", NS):
            name = element.get("name")
            if not name:
                continue
            max_occurs_raw = element.get("maxOccurs", "1")
            max_occurs = None if max_occurs_raw == "unbounded" else int(max_occurs_raw)
            fields.append(
                FieldDefinition(
                    name=name,
                    type_name=_local_name(element.get("type", "")) or None,
                    min_occurs=int(element.get("minOccurs", "1")),
                    max_occurs=max_occurs,
                    documentation=tuple(_clean_docs(element)),
                )
            )
        return fields

    def _append_payload(self, parent: ET.Element, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, list | tuple):
                for item in value:
                    self._append_value(parent, key, item)
            else:
                self._append_value(parent, key, value)

    def _append_value(self, parent: ET.Element, key: str, value: Any) -> None:
        child = ET.SubElement(parent, f"{{{self.namespace}}}{key}")
        if isinstance(value, dict):
            attrs = value.get("@attributes")
            if isinstance(attrs, dict):
                child.attrib.update({str(k): str(v) for k, v in attrs.items()})
            text = value.get("#text")
            if text is not None:
                child.text = self._scalar_to_text(text)
            self._append_payload(
                child, {k: v for k, v in value.items() if k not in {"@attributes", "#text"}}
            )
        else:
            child.text = self._scalar_to_text(value)

    def _element_to_payload(self, element: ET.Element) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for child in list(element):
            key = _local_name(child.tag)
            value: Any
            if list(child):
                value = self._element_to_payload(child)
                if child.attrib:
                    value["@attributes"] = {
                        _local_name(k): v for k, v in child.attrib.items()
                    }
                if child.text and child.text.strip():
                    value["#text"] = child.text.strip()
            else:
                value = child.text or ""
                if child.attrib:
                    value = {
                        "#text": value,
                        "@attributes": {_local_name(k): v for k, v in child.attrib.items()},
                    }
            if key in payload:
                if not isinstance(payload[key], list):
                    payload[key] = [payload[key]]
                payload[key].append(value)
            else:
                payload[key] = value
        return payload

    @staticmethod
    def _scalar_to_text(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
