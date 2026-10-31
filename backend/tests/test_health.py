from fastapi.testclient import TestClient

from app.main import app, create_app


def test_health():
    response = TestClient(app).get('/api/v1/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'recon-ai'}


def test_startup_without_llm_key(monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with TestClient(create_app()) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert client.post('/api/v1/recon', json={'target': 'example.com'}).status_code == 200


def test_cors_restricted():
    client = TestClient(app)
    headers = {'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'}
    assert client.options('/api/v1/recon', headers=headers).headers['access-control-allow-origin'] == headers['Origin']
    headers['Origin'] = 'https://untrusted.example'
    assert 'access-control-allow-origin' not in client.options('/api/v1/recon', headers=headers).headers


def test_http_error_envelope():
    response = TestClient(app).get('/missing')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'http_error'
