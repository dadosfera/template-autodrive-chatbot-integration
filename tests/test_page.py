"""Tests for the mock host page and its rendered widget config."""


def test_page_embeds_widget_and_container(client):
    html = client.get("/").text

    assert 'id="autodrive-chat"' in html
    assert "/chatbot/autodrive-chatbot.umd.cjs" in html
    assert "AutoDriveChat.init" in html


def test_page_never_leaks_the_client_secret(client):
    html = client.get("/").text

    assert "test-client-secret" not in html
    assert "clientSecret" not in html


def test_assistant_mode_includes_assistant_id(client):
    config = client.get("/api/autodrive/config").json()

    assert config["apiProfile"] == "assistant"
    assert config["assistantId"] == "assistant-456"
    assert config["datasetId"] == "dataset-123"
    assert config["tokenEndpoint"] == "/api/autodrive/chat-token"


def test_embed_mode_omits_assistant_id(make_client):
    config = make_client(autodrive_api_profile="embed").get(
        "/api/autodrive/config"
    ).json()

    assert config["apiProfile"] == "embed"
    assert "assistantId" not in config


def test_autodrive_url_points_at_assistant_api_not_this_host(client):
    config = client.get("/api/autodrive/config").json()

    assert config["autodriveUrl"].startswith("https://autodrive-assistant-api-")
    assert "testserver" not in config["autodriveUrl"]


def test_page_warns_about_unset_required_vars(make_client):
    html = make_client(autodrive_dataset_id="", autodrive_assistant_id="").get("/").text

    assert "Setup incomplete" in html
    assert "AUTODRIVE_DATASET_ID" in html
    assert "AUTODRIVE_ASSISTANT_ID" in html


def test_healthz_reports_configuration_state(client):
    payload = client.get("/healthz").json()

    assert payload["status"] == "ok"
    assert payload["credentials_configured"] is True
    assert payload["missing_required"] == []
