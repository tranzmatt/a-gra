# A-GRA UML Derivation Matrix

This matrix maps what can be derived from the current A-GRA artifacts.

## Source Artifacts Reviewed

- Schema/A-GRA_MessageDefinitions_v5_0_a.xsd
- Schema/A-GRA_SecurityMarkings_v5_0_a.xsd
- Documentation/ASK 5.0a ICD.pdf
- Documentation/ASK 5.0a Command and Control Interface Volume.pdf
- Documentation/ASK 5.0a Peer Interface Volume.pdf
- Documentation/ASK 5.0a Mission Systems Interface Volume.pdf
- Documentation/ASK 5.0a Vehicle Interface Volume.pdf
- Documentation/ASK 5.0a Mission Plan Interface Volume.pdf
- Documentation/ASK 5.0a Mission Debrief Interface Volume.pdf
- Documentation/ASK 5.0a MA L1 Compliance Document.pdf

## Key Structural Signals from XSD

- Top-level elements: 841
- Complex types: 4838 to 4845 range (depending on parser coverage)
- Complex type inheritance via extension: 2130
- Naming density:
  - Command: 232
  - CommandStatus: 116
  - Status: 334
  - Plan: 170
  - PlanCommand: 36
  - ApprovalStatus: 15
  - ExecutionStatus: 12
  - Request: 182
  - RequestStatus: 91
  - Capability: 74
  - Activity: 73

These naming patterns are ideal for deriving behavior and interaction UML.

## What We Can Derive

| UML Diagram Type | Primary Inputs | Confidence | What Can Be Auto-Derived Now | What Needs Human Mapping |
|---|---|---|---|---|
| Class Diagram | XSD complexType, element, extension | High | Classes, attributes, inheritance, associations by typed references | Semantic grouping and readability curation |
| Package Diagram | XSD naming clusters plus Interface Volume PDFs | High | Package/group boundaries by prefixes and interface family names | Final package boundaries tied to program intent |
| Sequence Diagram | ICD and Interface Volume sections titled Interface Interactions; XSD message names | Medium-High | Candidate message exchanges and ordered command/status pairs | Actor roles, branching logic, timing and retries |
| State Machine Diagram | XSD families CommandStatus, PlanStatus, ApprovalStatus, ExecutionStatus; ICD state text | Medium | Candidate states and transitions from status message lifecycles | Exact transition guards and exceptional paths |
| Activity Diagram | ICD workflow text and compliance process descriptions | Medium | Baseline flow blocks from procedural language | Decision nodes, concurrency and loop constraints |
| Component Diagram | Interface Volume ownership and subsystem boundaries | Medium | Components and interface connectors from documented interface boundaries | Runtime deployment details and protocol constraints |
| Use Case Diagram | ICD operational narratives and compliance requirements | Medium | Actors and high-level use cases from interface responsibilities | Goal decomposition and include/extend refinements |
| Object Diagram | Example payload instances (if available) | Low | Limited without canonical sample XML instances | Real instance snapshots from test vectors |
| Deployment Diagram | Not explicit in schema; partial in interface docs | Low | Very little from current artifacts | Environment, nodes, network, hosting topology |

## Priority Build Order

1. Class diagrams from XSD (already bootstrapped).
2. Package diagrams by interface family (C2, Peer, Mission Systems, Vehicle, Mission Plan, Mission Debrief).
3. Sequence diagrams from ICD Interface Interactions sections.
4. State machines for selected lifecycle-heavy entities (Plan and Command families).
5. Component diagrams for external/internal interface boundaries.

## Practical Derivation Rules

1. For each XSD element ending in Command, pair with CommandStatus for sequence lifelines.
2. For each Plan element family, derive PlanStatus and ExecutionStatus states first.
3. Use Request and RequestStatus pairings as asynchronous request/response interactions.
4. Use Capability and CapabilityStatus to model capability discovery/health states.
5. Keep one PlantUML file per interface family to avoid unrenderable mega-diagrams.

## Suggested File Targets

- uml/generated/class/
- uml/generated/package/
- uml/sequence/
- uml/state/
- uml/component/
- uml/usecase/

## Immediate Next Step

Generate split class and package diagrams by interface family from XSD name prefixes, then draft first sequence diagrams for Mission Plan and Mission Debrief interactions using ICD sections 1.2 Interface Interactions.
