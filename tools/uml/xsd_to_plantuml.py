#!/usr/bin/env python3
"""Generate PlantUML class diagrams from one or more XSD files.

This is intentionally simple and text-first:
- Reads top-level xs:element declarations (message-like roots)
- Reads xs:complexType fields and inheritance (xs:extension)
- Emits a single .puml file you can render with PlantUML
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

XSD_NS = {"xs": "http://www.w3.org/2001/XMLSchema"}


@dataclass
class FieldDef:
    name: str
    type_name: str


@dataclass
class TypeDef:
    name: str
    fields: List[FieldDef] = field(default_factory=list)
    base: Optional[str] = None


@dataclass
class ElementDef:
    name: str
    type_name: str


def local_name(qname: Optional[str]) -> str:
    if not qname:
        return "string"
    return qname.split(":")[-1]


def parse_complex_type(ct: ET.Element) -> TypeDef:
    type_name = ct.attrib.get("name", "AnonymousType")
    td = TypeDef(name=type_name)

    # Direct sequence fields
    for el in ct.findall("xs:sequence/xs:element", XSD_NS):
        td.fields.append(
            FieldDef(
                name=el.attrib.get("name", "unnamed"),
                type_name=local_name(el.attrib.get("type")),
            )
        )

    # Attributes
    for attr in ct.findall("xs:attribute", XSD_NS):
        td.fields.append(
            FieldDef(
                name=attr.attrib.get("name", "unnamedAttr"),
                type_name=local_name(attr.attrib.get("type")),
            )
        )

    # Complex content extension (inheritance + extra fields)
    ext = ct.find("xs:complexContent/xs:extension", XSD_NS)
    if ext is not None:
        td.base = local_name(ext.attrib.get("base"))
        for el in ext.findall("xs:sequence/xs:element", XSD_NS):
            td.fields.append(
                FieldDef(
                    name=el.attrib.get("name", "unnamed"),
                    type_name=local_name(el.attrib.get("type")),
                )
            )
        for attr in ext.findall("xs:attribute", XSD_NS):
            td.fields.append(
                FieldDef(
                    name=attr.attrib.get("name", "unnamedAttr"),
                    type_name=local_name(attr.attrib.get("type")),
                )
            )

    return td


def parse_xsd(path: str) -> tuple[List[ElementDef], Dict[str, TypeDef]]:
    tree = ET.parse(path)
    root = tree.getroot()

    elements: List[ElementDef] = []
    types: Dict[str, TypeDef] = {}

    for el in root.findall("xs:element", XSD_NS):
        elements.append(
            ElementDef(
                name=el.attrib.get("name", "UnnamedElement"),
                type_name=local_name(el.attrib.get("type")),
            )
        )

    for ct in root.findall("xs:complexType", XSD_NS):
        td = parse_complex_type(ct)
        types[td.name] = td

    return elements, types


def to_plantuml(elements: List[ElementDef], types: Dict[str, TypeDef], title: str) -> str:
    lines: List[str] = []
    lines.append("@startuml")
    lines.append("hide circle")
    lines.append("skinparam classAttributeIconSize 0")
    lines.append(f"title {title}")
    lines.append("")

    # Element roots as entry points
    for el in sorted(elements, key=lambda x: x.name):
        lines.append(f'class "{el.name}" <<element>> {{')
        lines.append(f"  +type: {el.type_name}")
        lines.append("}")

    lines.append("")

    for tname in sorted(types.keys()):
        td = types[tname]
        lines.append(f'class "{td.name}" <<complexType>> {{')
        if td.fields:
            for f in td.fields:
                lines.append(f"  +{f.name}: {f.type_name}")
        else:
            lines.append("  --")
        lines.append("}")

    lines.append("")

    known_types: Set[str] = set(types.keys())

    for el in sorted(elements, key=lambda x: x.name):
        lines.append(f'"{el.name}" --> "{el.type_name}" : payload')

    for tname in sorted(types.keys()):
        td = types[tname]
        if td.base:
            lines.append(f'"{td.base}" <|-- "{td.name}"')
        for f in td.fields:
            if f.type_name in known_types:
                lines.append(f'"{td.name}" --> "{f.type_name}" : {f.name}')

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert XSD to PlantUML classes")
    parser.add_argument(
        "xsd",
        nargs="+",
        help="Input XSD files (pass both schema files for a combined model)",
    )
    parser.add_argument("-o", "--output", required=True, help="Output .puml path")
    parser.add_argument("--title", default="XSD Model", help="Diagram title")
    args = parser.parse_args()

    all_elements: List[ElementDef] = []
    all_types: Dict[str, TypeDef] = {}

    for path in args.xsd:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        elements, types = parse_xsd(path)
        all_elements.extend(elements)
        all_types.update(types)

    puml = to_plantuml(all_elements, all_types, args.title)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(puml)

    print(f"Wrote {args.output}")
    print(f"Elements: {len(all_elements)}")
    print(f"Complex types: {len(all_types)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
