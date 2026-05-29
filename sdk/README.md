# A-GRA Python SDK

This SDK provides a small, dependency-free implementation layer for the A-GRA 5.0a interface mechanisms described by the ICD PDFs and encoded in the XSD schemas.

It is intentionally schema-driven. The package reads `Schema/A-GRA_MessageDefinitions_v5_0_a.xsd` and `Schema/A-GRA_SecurityMarkings_v5_0_a.xsd` at runtime, then exposes:

- message registry lookup by top-level UCI/A-GRA message name
- primitive categorization such as `Data-1`, `Command-2`, `Status-1`, and `ActionRequest-2`
- XML serialization and parsing for arbitrary schema messages
- security marking helpers
- in-memory publish/subscribe and request/command lifecycle helpers
- lightweight sequence and message compliance checks

## Quick Start

```python
from agra_sdk import AgraMessage, MessageBus, SchemaRepository, SecurityInformation

schema = SchemaRepository.from_default_paths()
security = SecurityInformation.unclassified(owner_producer="USA")

message = AgraMessage(
    name="ActionCommand",
    payload={
        "MessageData": {
            "SecurityInformation": security.to_payload(),
        },
    },
)

xml_text = schema.to_xml(message)
round_trip = schema.from_xml(xml_text)

bus = MessageBus(schema)
bus.publish(round_trip)
```

The SDK does not try to generate thousands of static classes from the XSD. A-GRA message payloads are nested dictionaries so implementers can work with the full schema surface without regenerating code.

## CLI

From this folder:

```bash
python -m agra_sdk.cli list --primitive Command-2
python -m agra_sdk.cli describe ActionCommand
python -m agra_sdk.cli enums ClassificationEnum
```

