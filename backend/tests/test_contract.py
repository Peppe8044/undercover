from backend.main import app

METHODS = {"get", "post", "put", "patch", "delete"}


def body_schema(spec, operation):
    content = operation.get("requestBody", {}).get("content", {})
    if not content:
        return None
    ref = content["application/json"]["schema"]["$ref"]
    return spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def test_every_operation_follows_the_standard():
    spec = app.openapi()
    operations = [
        operation
        for item in spec["paths"].values()
        for method, operation in item.items()
        if method in METHODS
    ]
    assert operations
    for operation in operations:
        assert operation["operationId"]
        assert operation["description"]
        assert "\n" not in operation["description"].strip()
        assert all(
            parameter["required"] for parameter in operation.get("parameters", [])
        )
        schema = body_schema(spec, operation)
        if schema:
            assert operation["requestBody"]["required"]
            assert set(schema["properties"]) == set(schema["required"])
