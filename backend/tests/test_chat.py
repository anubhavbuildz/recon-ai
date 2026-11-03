import asyncio
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.config import Settings
from app.service.llm.base import ModelError
from app.service.llm.workflow import chain
from app.service.provide.aws.base import Aws
from app.service.tools import call_s3


def request(arguments=None, name="call_s3"):
    if isinstance(arguments, str):
        return AIMessage(
            content="",
            invalid_tool_calls=[
                {"name": name, "args": arguments, "id": "call_123", "error": "invalid"}
            ],
        )
    return AIMessage(
        content="",
        tool_calls=[{"id": "call_123", "name": name, "args": arguments or {}}],
    )


def setup(monkeypatch, first=None):
    monkeypatch.setattr(
        chain,
        "get_settings",
        lambda: Settings(s3_bucket_name="bucket", s3_object_key="key"),
    )
    provider = Mock()
    provider.read_configured_text.return_value = "Resources: sample"
    monkeypatch.setattr(call_s3, "Aws", Mock(return_value=provider))
    client = Mock(close=AsyncMock())
    client.bound = Mock(
        ainvoke=AsyncMock(side_effect=[first or request(), AIMessage(content="Answer")])
    )
    client.bind_tools.return_value = client.bound
    monkeypatch.setattr(chain, "LLMClient", Mock(return_value=client))
    return provider, client


def test_chat_pipeline_and_cleanup(monkeypatch):
    provider, client = setup(monkeypatch)
    result = asyncio.run(chain.run_chat_workflow("Question"))
    assert result.message == "Answer"
    assert result.source == "s3://bucket/key"
    assert client.bound.ainvoke.await_count == 2
    messages = client.bound.ainvoke.call_args.args[0]
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "Question"
    assert isinstance(messages[-1], ToolMessage)
    assert messages[-1].tool_call_id == "call_123"
    assert messages[-1].content == "Resources: sample"
    assert client.bind_tools.call_args.kwargs["tool_choice"] == "auto"
    provider.read_configured_text.assert_called_once()
    client.close.assert_awaited_once()
    provider.aws_client.close.assert_called_once()


def test_s3_failure_closes_clients(monkeypatch):
    provider, client = setup(monkeypatch)
    provider.read_configured_text.side_effect = ValueError("too large")
    with pytest.raises(ValueError):
        asyncio.run(chain.run_chat_workflow("Question"))
    assert client.bound.ainvoke.await_count == 1
    client.close.assert_awaited_once()
    provider.aws_client.close.assert_called_once()


@pytest.mark.parametrize(
    "model_request",
    [
        request("{bad"),
        request({"bucket": "other"}),
        request(name="unknown"),
        AIMessage(content="No tool"),
    ],
)
def test_invalid_tool_requests_never_read_s3(monkeypatch, model_request):
    provider, client = setup(monkeypatch, model_request)
    with pytest.raises(ModelError):
        asyncio.run(chain.run_chat_workflow("Question"))
    provider.read_configured_text.assert_not_called()
    client.close.assert_awaited_once()


@pytest.mark.parametrize(
    "data,limit,valid",
    [
        (b"hello", 10, True),
        (b"long data", 4, False),
        (b"\xff", 10, False),
        (b"", 10, False),
    ],
)
def test_bounded_read(data, limit, valid):
    provider = Aws.__new__(Aws)
    provider.settings = Settings(
        s3_bucket_name="bucket", s3_object_key="key", s3_max_bytes=limit
    )
    body = BytesIO(data)
    provider.aws_client = Mock()
    provider.aws_client.get_object.return_value = {"Body": body}
    if valid:
        assert provider.read_configured_text() == "hello"
    else:
        with pytest.raises(ValueError):
            provider.read_configured_text()
    assert body.closed


def test_repeated_tool_call_is_not_executed(monkeypatch):
    provider, client = setup(monkeypatch)
    client.bound.ainvoke.side_effect = [request(), request()]
    with pytest.raises(ModelError, match="no final answer"):
        asyncio.run(chain.run_chat_workflow("Question"))
    provider.read_configured_text.assert_called_once()
    assert client.bound.ainvoke.await_count == 2
    client.close.assert_awaited_once()


def test_history_tool_and_multiple_sources(monkeypatch):
    import json

    provider, client = setup(monkeypatch)
    monkeypatch.setattr(
        chain,
        "get_settings",
        lambda: Settings(s3_bucket_name="bucket", s3_snapshot_prefix="snapshots/"),
    )
    sources = [
        "s3://bucket/snapshots/2026/11/03/a.json",
        "s3://bucket/snapshots/2026/11/02/b.json",
    ]
    provider.read_snapshot_history.return_value = json.dumps(
        {
            "snapshots": [{"source": source, "data": {}} for source in sources],
            "missing_dates": ["2026-11-01"],
        }
    )
    response = asyncio.run(chain.run_chat_workflow("Compare today and yesterday"))
    assert response.sources == sources
    assert response.source == sources[0]
    provider.read_snapshot_history.assert_called_once()
    provider.read_configured_text.assert_not_called()
    provider.aws_client.close.assert_called_once()
