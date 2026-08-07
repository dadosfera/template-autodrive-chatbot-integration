import pytest
from fastapi.testclient import TestClient

from src.config import Settings, get_settings
from src.main import app

BASE_ENV = {
    "autodrive_auth_client_id": "test-client-id",
    "autodrive_auth_client_secret": "test-client-secret",
    "autodrive_url": "https://autodrive-assistant-api-test.stg.dadosfera.ai",
    "autodrive_dataset_id": "dataset-123",
    "autodrive_assistant_id": "assistant-456",
    "autodrive_api_profile": "assistant",
    "autodrive_mock_token": False,
}


@pytest.fixture
def make_client():
    """Build a TestClient whose settings are overridden per test."""

    def _make(**overrides):
        # _env_file=None keeps a developer's local .env out of the test run.
        settings = Settings(_env_file=None, **{**BASE_ENV, **overrides})
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client):
    return make_client()
