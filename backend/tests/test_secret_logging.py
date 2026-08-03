"""Regression tests for sensitive WebSocket logging."""

import ast
import inspect
import logging
import textwrap
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.websockets import WebSocketState

from routers import websocket as websocket_router


LOG_TEMPLATE = "websocket request_id=%s result=%s"
ALLOWED_RESULTS = {
    "accepted",
    "authentication_failed",
    "cancelled",
    "disconnected",
    "internal_error",
    "invalid_query",
    "metrics_sent",
    "send_failed",
}


class StubWebSocket:
    def __init__(self, query_string: bytes, *, disconnect_on_accept: bool = False):
        self.scope = {"query_string": query_string}
        self.client_state = WebSocketState.CONNECTED
        self.disconnect_on_accept = disconnect_on_accept
        self.accepted = False
        self.close_code = None
        self.close_reason = None
        self.send_error = None

    async def accept(self):
        self.accepted = True
        if self.disconnect_on_accept:
            self.client_state = WebSocketState.DISCONNECTED

    async def close(self, code=None, reason=None):
        self.close_code = code
        self.close_reason = reason
        self.client_state = WebSocketState.DISCONNECTED

    async def receive_json(self):
        return {"type": "authenticate", "ticket": "test-ticket"}

    async def send_json(self, payload):
        if self.send_error is not None:
            raise self.send_error


def _messages(caplog):
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == websocket_router.__name__
        and record.getMessage().startswith("websocket ")
    ]


def _assert_sensitive_values_absent(caplog, *sensitive_values):
    output = "\n".join(record.getMessage() for record in caplog.records)
    forbidden_labels = ("query_string", "token_present")
    if any(value in output for value in sensitive_values):
        pytest.fail("sensitive websocket data leaked into logs", pytrace=False)
    if any(label in output for label in forbidden_labels):
        pytest.fail("sensitive websocket metadata leaked into logs", pytrace=False)


def _assert_structured_result_messages(messages):
    if not messages:
        pytest.fail("expected a structured websocket result log", pytrace=False)

    for message in messages:
        fields = message.split()
        if len(fields) != 3:
            pytest.fail("websocket result log contains unexpected fields", pytrace=False)
        if fields[0] != "websocket":
            pytest.fail("websocket result log has an unexpected prefix", pytrace=False)
        if not fields[1].startswith("request_id="):
            pytest.fail("websocket result log is missing a request ID", pytrace=False)
        request_id = fields[1].removeprefix("request_id=")
        if len(request_id) != 32 or any(char not in "0123456789abcdef" for char in request_id):
            pytest.fail("websocket result log has an invalid request ID", pytrace=False)
        if fields[2].removeprefix("result=") not in ALLOWED_RESULTS:
            pytest.fail("websocket result log has an unexpected result", pytrace=False)


def test_websocket_endpoint_logging_calls_have_only_request_id_and_result():
    """Static guard: endpoint logging cannot interpolate request/query values."""
    source = textwrap.dedent(inspect.getsource(websocket_router.websocket_monitor))
    tree = ast.parse(source)
    logging_calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "logger":
            continue
        logging_calls.append(node)

    if not logging_calls:
        pytest.fail("websocket endpoint has no auditable result logging", pytrace=False)

    for call in logging_calls:
        if len(call.args) != 3:
            pytest.fail("websocket logging call contains unexpected fields", pytrace=False)
        template, request_id, result = call.args
        if not isinstance(template, ast.Constant) or template.value != LOG_TEMPLATE:
            pytest.fail("websocket logging call does not use the safe template", pytrace=False)
        if not isinstance(request_id, ast.Name) or request_id.id != "request_id":
            pytest.fail("websocket logging call does not use the server request ID", pytrace=False)
        if not isinstance(result, ast.Constant) or result.value not in ALLOWED_RESULTS:
            pytest.fail("websocket logging call has a non-constant result", pytrace=False)


@pytest.mark.asyncio
async def test_rejected_websocket_does_not_log_token_or_query(caplog):
    sensitive_value = "sensitive-" + uuid4().hex
    sensitive_query_value = "query-" + uuid4().hex
    query = f"token={sensitive_value}&diagnostic={sensitive_query_value}".encode()
    websocket = StubWebSocket(query)
    caplog.set_level(logging.DEBUG, logger=websocket_router.__name__)

    await websocket_router.websocket_monitor(websocket)

    _assert_sensitive_values_absent(caplog, sensitive_value, sensitive_query_value)
    messages = _messages(caplog)
    _assert_structured_result_messages(messages)
    assert [message.rsplit("=", 1)[-1] for message in messages] == [
        "authentication_failed"
    ]
    assert websocket.close_code == 4001


@pytest.mark.asyncio
async def test_invalid_query_log_does_not_include_raw_bytes(caplog):
    sensitive_value = ("sensitive-" + uuid4().hex).encode()
    websocket = StubWebSocket(b"token=" + sensitive_value + b"\xff")
    caplog.set_level(logging.DEBUG, logger=websocket_router.__name__)

    await websocket_router.websocket_monitor(websocket)

    _assert_sensitive_values_absent(caplog, sensitive_value.decode())
    messages = _messages(caplog)
    _assert_structured_result_messages(messages)
    assert [message.rsplit("=", 1)[-1] for message in messages] == [
        "authentication_failed"
    ]
    assert websocket.close_code == 4001


@pytest.mark.asyncio
async def test_accepted_websocket_logs_only_request_id_and_results(monkeypatch, caplog):
    websocket = StubWebSocket(b"", disconnect_on_accept=True)
    monkeypatch.setattr(websocket_router, "_authenticate_monitor_ticket", lambda ws: _true())
    caplog.set_level(logging.DEBUG, logger=websocket_router.__name__)

    await websocket_router.websocket_monitor(websocket)

    _assert_sensitive_values_absent(caplog, "test-ticket")
    messages = _messages(caplog)
    _assert_structured_result_messages(messages)
    assert [message.rsplit("=", 1)[-1] for message in messages] == [
        "accepted",
        "disconnected",
    ]
    assert websocket.accepted is True


@pytest.mark.asyncio
async def test_websocket_runtime_error_detail_is_not_logged(monkeypatch, caplog):
    sensitive_value = "sensitive-" + uuid4().hex
    websocket = StubWebSocket(b"")
    websocket.send_error = RuntimeError("transport-" + sensitive_value)
    monkeypatch.setattr(websocket_router, "_authenticate_monitor_ticket", lambda ws: _true())

    # PERF-01: monitor 루프는 이제 단일 수집기의 공유 snapshot을 구독한다.
    # 즉시 하나의 snapshot을 전달하는 fake 수집기를 주입해 send 경로를 구동한다.
    class _FakeCollector:
        def get_latest(self):
            return None

        async def wait_for_update(self):
            return SimpleNamespace(model_dump=lambda: {})

    monkeypatch.setattr(websocket_router, "get_collector", lambda: _FakeCollector())
    caplog.set_level(logging.DEBUG, logger=websocket_router.__name__)

    await websocket_router.websocket_monitor(websocket)

    _assert_sensitive_values_absent(caplog, sensitive_value)
    messages = _messages(caplog)
    _assert_structured_result_messages(messages)
    assert [message.rsplit("=", 1)[-1] for message in messages] == [
        "accepted",
        "send_failed",
    ]


async def _true():
    return True
