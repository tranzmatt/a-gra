from agra_sdk import (
    AgraMessage,
    InteractionValidator,
    MessageBus,
    Primitive,
    SchemaRepository,
    SecurityInformation,
)


def test_schema_loads_messages_and_enums():
    schema = SchemaRepository.from_default_paths(".")
    assert len(schema.messages) > 800
    assert schema.describe("ActionCommand").primitive == Primitive.COMMAND
    assert "U" in schema.enum_values("ClassificationEnum")


def test_xml_round_trip_and_bus_subscription():
    schema = SchemaRepository.from_default_paths(".")
    message = AgraMessage(
        "ActionCommand",
        {"MessageData": {"SecurityInformation": SecurityInformation.unclassified().to_payload()}},
    )

    issues = InteractionValidator(schema).validate_message(message)
    assert issues == []

    xml_text = schema.to_xml(message)
    parsed = schema.from_xml(xml_text)
    assert parsed.name == "ActionCommand"
    assert parsed.payload["MessageData"]["SecurityInformation"]["Classification"] == "U"

    seen = []
    bus = MessageBus(schema)
    bus.subscribe_primitive(Primitive.COMMAND, lambda envelope: seen.append(envelope.message.name))
    bus.publish(parsed)
    assert seen == ["ActionCommand"]
