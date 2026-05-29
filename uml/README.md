# A-GRA UML Generation

Yes, XSD is XML and can be parsed directly. This repo uses a small script to convert XSD structure into PlantUML text.

## Inputs

- Schema/A-GRA_MessageDefinitions_v5_0_a.xsd
- Schema/A-GRA_SecurityMarkings_v5_0_a.xsd

## Generate PlantUML

Run from repo root:

```bash
python3 tools/uml/xsd_to_plantuml.py \
  Schema/A-GRA_MessageDefinitions_v5_0_a.xsd \
  Schema/A-GRA_SecurityMarkings_v5_0_a.xsd \
  -o uml/generated/a-gra-schema.puml \
  --title "A-GRA ASK 5.0a Schema"
```

## Render to SVG (optional)

If PlantUML is installed:

```bash
plantuml -tsvg uml/generated/a-gra-schema.puml
```

## Notes

- This is a first-pass structural diagram (elements, complex types, extensions, and type references).
- ICD sequence/interaction diagrams should be authored separately as PlantUML sequence diagrams using message flows from the ICD PDF.
