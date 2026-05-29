from __future__ import annotations

import argparse
import json

from .schema import SchemaRepository


def _schema(args: argparse.Namespace) -> SchemaRepository:
    return SchemaRepository.from_default_paths(args.repo_root)


def cmd_list(args: argparse.Namespace) -> int:
    schema = _schema(args)
    messages = schema.messages_by_primitive(args.primitive) if args.primitive else sorted(
        schema.messages.values(), key=lambda item: item.name
    )
    for item in messages:
        primitive = item.primitive or "-"
        print(f"{item.name}\t{primitive}\t{item.type_name}\t{item.version or '-'}")
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    schema = _schema(args)
    message = schema.describe(args.message)
    type_def = schema.type_for_message(args.message)
    print(json.dumps({
        "name": message.name,
        "type": message.type_name,
        "version": message.version,
        "primitive": message.primitive,
        "documentation": message.documentation,
        "fields": [
            {
                "name": field.name,
                "type": field.type_name,
                "required": field.required,
                "repeated": field.repeated,
                "min_occurs": field.min_occurs,
                "max_occurs": field.max_occurs,
            }
            for field in (type_def.fields if type_def else ())
        ],
    }, indent=2))
    return 0


def cmd_enums(args: argparse.Namespace) -> int:
    schema = _schema(args)
    for value in schema.enum_values(args.type_name):
        print(value)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agra-sdk")
    parser.add_argument("--repo-root", default=None)
    sub = parser.add_subparsers(required=True)

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--primitive", default=None)
    list_parser.set_defaults(func=cmd_list)

    describe_parser = sub.add_parser("describe")
    describe_parser.add_argument("message")
    describe_parser.set_defaults(func=cmd_describe)

    enum_parser = sub.add_parser("enums")
    enum_parser.add_argument("type_name")
    enum_parser.set_defaults(func=cmd_enums)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
