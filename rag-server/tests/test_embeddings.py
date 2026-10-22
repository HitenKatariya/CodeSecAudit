"""Unit test for the NVIDIA NIM input_type passthrough in EmbeddingClient."""

import httpx
from app.embeddings.model import EmbeddingClient


def _client_with_captured_payload(captured: dict):
    import json as _json

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = _json.loads(request.content)
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]})

    client = EmbeddingClient(model_name="test-model", api_base="https://example.test", dimension=2)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_input_type_included_when_passed():
    captured = {}
    client = _client_with_captured_payload(captured)
    client.encode(["hello"], input_type="query")
    assert captured["payload"]["input_type"] == "query"


def test_input_type_omitted_by_default():
    captured = {}
    client = _client_with_captured_payload(captured)
    client.encode(["hello"])
    assert "input_type" not in captured["payload"]
