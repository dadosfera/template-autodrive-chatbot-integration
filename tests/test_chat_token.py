"""Tests for the tokenEndpoint the widget calls."""

import httpx
import respx

TOKEN_URL = "https://autodrive-assistant-api-test.stg.dadosfera.ai/auth/token"


@respx.mock
def test_converts_camel_case_response_to_widget_contract(client):
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "accessToken": "upstream-token",
                "tokenType": "Bearer",
                "expiresIn": 300,
            },
        )
    )

    response = client.post("/api/autodrive/chat-token")

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "upstream-token",
        "token_type": "Bearer",
        "expires_in": 300,
    }
    assert route.called


@respx.mock
def test_sends_credentials_server_to_server(client):
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"accessToken": "t"})
    )

    client.post("/api/autodrive/chat-token")

    import json

    body = json.loads(route.calls.last.request.content)
    assert body == {
        "clientId": "test-client-id",
        "clientSecret": "test-client-secret",
    }


@respx.mock
def test_defaults_token_type_and_expiry_when_absent(client):
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"accessToken": "only-token"})
    )

    payload = client.post("/api/autodrive/chat-token").json()

    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 300


@respx.mock
def test_upstream_rejection_becomes_502(client):
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(401, json={"detail": "invalid credentials"})
    )

    response = client.post("/api/autodrive/chat-token")

    assert response.status_code == 502
    assert response.json()["upstream_status"] == 401


@respx.mock
def test_missing_access_token_becomes_502(client):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"foo": "bar"}))

    assert client.post("/api/autodrive/chat-token").status_code == 502


@respx.mock
def test_network_failure_becomes_502(client):
    respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("unreachable"))

    assert client.post("/api/autodrive/chat-token").status_code == 502


def test_mock_mode_issues_token_without_upstream(make_client):
    client = make_client(autodrive_mock_token=True)

    payload = client.post(
        "/api/autodrive/chat-token", headers={"X-Mock-User": "user-9"}
    ).json()

    assert payload["access_token"] == "mock-access-token-for-user-9"
    assert payload["token_type"] == "Bearer"


def test_missing_credentials_is_a_server_error(make_client):
    client = make_client(
        autodrive_auth_client_id="", autodrive_auth_client_secret=""
    )

    response = client.post("/api/autodrive/chat-token")

    assert response.status_code == 500
    assert "AUTODRIVE_AUTH_CLIENT_ID" in response.json()["detail"]
