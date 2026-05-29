#!/usr/bin/env python3
"""Generate split PlantUML diagrams from XSD files.

Creates smaller, focused diagrams by:
- lifecycle categories (Command, Status, Plan, Request, etc.)
- top acronym families (for element names that use PREFIX_*)
"""

from __future__ import annotations

import argparse
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

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

    for el in ct.findall("xs:sequence/xs:element", XSD_NS):
        td.fields.append(
            FieldDef(
                name=el.attrib.get("name", "unnamed"),
                type_name=local_name(el.attrib.get("type")),
            )
        )

    for attr in ct.findall("xs:attribute", XSD_NS):
        td.fields.append(
            FieldDef(
                name=attr.attrib.get("name", "unnamedAttr"),
                type_name=local_name(attr.attrib.get("type")),
            )
        )

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


def parse_xsd(path: str) -> Tuple[List[ElementDef], Dict[str, TypeDef]]:
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


def collect_related_types(seed_types: Iterable[str], types: Dict[str, TypeDef], cap: int = 700) -> Tuple[Set[str], bool]:
    seen: Set[str] = set()
    queue: List[str] = [t for t in seed_types if t in types]
    truncated = False

    while queue:
        t = queue.pop(0)
        if t in seen:
            continue
        seen.add(t)
        if len(seen) >= cap:
            truncated = True
            break

        td = types.get(t)
        if not td:
            continue

        if td.base and td.base in types and td.base not in seen:
            queue.append(td.base)

        for f in td.fields:
            if f.type_name in types and f.type_name not in seen:
                queue.append(f.type_name)

    return seen, truncated


def to_plantuml(
    title: str,
    elements: List[ElementDef],
    types: Dict[str, TypeDef],
    selected_elements: List[ElementDef],
    selected_type_names: Set[str],
) -> str:
    lines: List[str] = []
    lines.append("@startuml")
    lines.append("hide circle")
    lines.append("skinparam classAttributeIconSize 0")
    lines.append(f"title {title}")
    lines.append("")

    for el in sorted(selected_elements, key=lambda x: x.name):
        lines.append(f'class "{el.name}" <<element>> {{')
        lines.append(f"  +type: {el.type_name}")
        lines.append("}")

    lines.append("")

    for tname in sorted(selected_type_names):
        td = types.get(tname)
        if not td:
            continue
        lines.append(f'class "{td.name}" <<complexType>> {{')
        if td.fields:
            for f in td.fields:
                if f.type_name in selected_type_names:
                    lines.append(f"  +{f.name}: {f.type_name}")
                else:
                    lines.append(f"  +{f.name}: {f.type_name}")
        else:
            lines.append("  --")
        lines.append("}")

    lines.append("")

    for el in sorted(selected_elements, key=lambda x: x.name):
        if el.type_name in selected_type_names:
            lines.append(f'"{el.name}" --> "{el.type_name}" : payload')

    for tname in sorted(selected_type_names):
        td = types.get(tname)
        if not td:
            continue
        if td.base and td.base in selected_type_names:
            lines.append(f'"{td.base}" <|-- "{td.name}"')
        for f in td.fields:
            if f.type_name in selected_type_names:
                lines.append(f'"{td.name}" --> "{f.type_name}" : {f.name}')

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def prefix_family(name: str) -> Optional[str]:
    if "_" not in name:
        return None
    fam = name.split("_", 1)[0]
    if re.fullmatch(r"[A-Z0-9]{2,12}", fam):
        return fam
    return None


def build_groups(elements: List[ElementDef]) -> List[Tuple[str, str, Callable[[ElementDef], bool]]]:
    groups: List[Tuple[str, str, Callable[[ElementDef], bool]]] = [
        ("lifecycle-command", "Lifecycle: Command", lambda e: e.name.endswith("Command") and not e.name.endswith("PlanCommand")),
        ("lifecycle-command-status", "Lifecycle: CommandStatus", lambda e: e.name.endswith("CommandStatus")),
        ("lifecycle-request", "Lifecycle: Request", lambda e: e.name.endswith("Request") and not e.name.endswith("RequestStatus")),
        ("lifecycle-request-status", "Lifecycle: RequestStatus", lambda e: e.name.endswith("RequestStatus")),
        ("lifecycle-plan", "Lifecycle: Plan", lambda e: e.name.endswith("Plan") and not e.name.endswith("PlanStatus") and not e.name.endswith("PlanCommand") and not e.name.endswith("PlanExecutionStatus") and not e.name.endswith("PlanApprovalStatus")),
        ("lifecycle-plan-command", "Lifecycle: PlanCommand", lambda e: e.name.endswith("PlanCommand")),
        ("lifecycle-status", "Lifecycle: Status", lambda e: e.name.endswith("Status") and not e.name.endswith("CommandStatus") and not e.name.endswith("RequestStatus")),
        ("lifecycle-capability", "Lifecycle: Capability", lambda e: "Capability" in e.name),
        ("lifecycle-activity", "Lifecycle: Activity", lambda e: "Activity" in e.name),
    ]

    family_counts = Counter()
    for e in elements:
        fam = prefix_family(e.name)
        if fam:
            family_counts[fam] += 1

    for fam, count in family_counts.most_common():
        if count < 5:
            continue
        slug = f"family-{fam.lower()}"
        title = f"Family: {fam}_*"
        groups.append((slug, title, lambda e, f=fam: e.name.startswith(f"{f}_")))

    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description="Split XSD model into focused PlantUML diagrams")
    parser.add_argument("xsd", nargs="+", help="Input XSD files")
    parser.add_argument("--out-dir", required=True, help="Output directory for split .puml files")
    parser.add_argument("--title-prefix", default="A-GRA ASK 5.0a", help="Title prefix")
    parser.add_argument("--type-cap", type=int, default=700, help="Maximum related types included per diagram")
    args = parser.parse_args()

    all_elements: List[ElementDef] = []
    all_types: Dict[str, TypeDef] = {}

    for path in args.xsd:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        elements, types = parse_xsd(path)
        all_elements.extend(elements)
        all_types.update(types)

    os.makedirs(args.out_dir, exist_ok=True)

    groups = build_groups(all_elements)
    summary_lines = ["# Split UML Summary", "", f"Total elements: {len(all_elements)}", f"Total complex types: {len(all_types)}", "", "| File | Elements | Types | Notes |", "|---|---:|---:|---|"]

    for slug, gtitle, pred in groups:
        selected_elements = [e for e in all_elements if pred(e)]
        if not selected_elements:
            continue

        seed_types = [e.type_name for e in selected_elements]
        selected_types, truncated = collect_related_types(seed_types, all_types, cap=args.type_cap)
        if not selected_types:
            selected_types = {t for t in seed_types if t in all_types}

        title = f"{args.title_prefix} - {gtitle}"
        puml = to_plantuml(title, all_elements, all_types, selected_elements, selected_types)

        out_path = os.path.join(args.out_dir, f"{slug}.puml")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(puml)

        note = "truncated type closure" if truncated else ""
        summary_lines.append(f"| {os.path.basename(out_path)} | {len(selected_elements)} | {len(selected_types)} | {note} |")
        print(f"Wrote {out_path} (elements={len(selected_elements)} types={len(selected_types)}{', truncated' if truncated else ''})")

    summary_path = os.path.join(args.out_dir, "README.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")
    print(f"Wrote {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
