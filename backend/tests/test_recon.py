from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.schemas import ReconResponse
from app.main import app
from app.service.llm.workflow import graph
from app.service.tools.policy import require_execution_permission
from app.service.tools.registry import list_tools

client = TestClient(app)


@pytest.mark.parametrize(('target', 'domain'), [
    ('example.com', 'example.com'),
    ('  EXAMPLE.COM  ', 'example.com'),
    ('https://Example.com/path?q=1#section', 'example.com'),
    ('https://sub.example.com:8443/', 'sub.example.com'),
    ('example.com.', 'example.com'),
    ('xn--bcher-kva.de', 'xn--bcher-kva.de'),
])
def test_valid_target(target, domain):
    response = client.post('/api/v1/recon', json={'target': target})
    assert response.status_code == 200
    assert response.json() == {
        'target': domain, 'status': 'not_executed',
        'message': 'Reconnaissance tools are not configured yet.', 'agents': [],
    }


@pytest.mark.parametrize('target', [
    '', 'invalid', 'bad_domain.com', '-bad.example', 'bad-.example',
    'example..com', 'example.com/path', 'example.com:443',
    'http://example.com', 'ftp://example.com', '//example.com',
    'https://user:pass@example.com', 'https://@example.com',
    'localhost', 'localhost.', 'https://localhost', 'sub.localhost',
    '127.0.0.1', 'https://127.0.0.1', 'https://[::1]', '::1',
    'https://[2001:db8::1]', '2130706433', 'https://2130706433',
    'https://example.com:bad', 'https://example.com:65536',
    'https://example.com:0', 'https://example.com:', 'https://', 'https://example.com\\evil',
    'https://exam\nple.com', 'https://exa mple.com',
    'https://example.com/%0a@evil.com\x00',
    'a' * 64 + '.com', 'https://example.com%2fevil.com',
])
def test_invalid_target(target):
    response = client.post('/api/v1/recon', json={'target': target})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'validation_error'
    assert response.json()['error']['details']


@pytest.mark.parametrize('payload', [{}, {'target': None}, {'target': 12}, {'target': []}, {'target': 'example.com', 'extra': True}])
def test_invalid_payload(payload):
    assert client.post('/api/v1/recon', json=payload).status_code == 422


def test_workflow_invocation(monkeypatch):
    run = AsyncMock(return_value=ReconResponse(target='example.com'))
    monkeypatch.setattr(graph, 'run_workflow', run)
    response = client.post('/api/v1/recon', json={'target': 'https://EXAMPLE.com/a'})
    assert response.status_code == 200
    run.assert_awaited_once_with('example.com')


def test_real_graph_calls_agent(monkeypatch):
    agent = AsyncMock(return_value=ReconResponse(target='example.com'))
    monkeypatch.setattr(graph, 'run_recon_agent', agent)
    assert client.post('/api/v1/recon', json={'target': 'example.com'}).status_code == 200
    agent.assert_awaited_once_with('example.com')


def test_no_external_execution(monkeypatch):
    import socket
    import subprocess
    import httpx
    from openai import AsyncOpenAI

    def forbidden(*args, **kwargs):
        pytest.fail('Outbound network, process, or LLM access attempted')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, 'send', forbidden)
    monkeypatch.setattr(AsyncOpenAI, '__init__', forbidden)
    response = client.post('/api/v1/recon', json={'target': 'example.com'})
    assert response.status_code == 200
    assert response.json()['status'] == 'not_executed'
    assert all(not tool.configured for tool in list_tools())


@pytest.mark.parametrize('authorized,scope', [(False, frozenset()), (True, frozenset()), (True, frozenset({'example.com'}))])
def test_nmap_never_executes(authorized, scope):
    nmap = next(tool for tool in list_tools() if tool.name == 'Nmap')
    assert nmap.active
    with pytest.raises(PermissionError):
        require_execution_permission(nmap, 'example.com', explicit_authorization=authorized, approved_scope=scope)


def test_internal_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(graph, 'run_workflow', AsyncMock(side_effect=RuntimeError('secret detail')))
    response = TestClient(app, raise_server_exceptions=False).post('/api/v1/recon', json={'target': 'example.com'}, headers={'Origin': 'http://localhost:5173'})
    assert response.status_code == 500
    assert response.json() == {'error': {'code': 'internal_error', 'message': 'An internal error occurred'}}
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
