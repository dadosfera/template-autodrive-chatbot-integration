"""Mock host application for the AutoDrive Chatbot widget.

Serves two things:

1. ``GET /`` — a mock page that embeds the widget via ``AutoDriveChat.init``.
2. ``POST /api/autodrive/chat-token`` — the ``tokenEndpoint`` the widget calls.
   It exchanges the server-side client credentials for a short-lived token and
   converts the Assistant API's camelCase response into the snake_case contract
   the widget expects.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .config import Settings, get_settings

logger = logging.getLogger("autodrive.mock")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

TOKEN_TIMEOUT_SECONDS = 10.0
DEFAULT_EXPIRES_IN = 300

app = FastAPI(
    title="AutoDrive Chatbot Integration — Mock Host",
    description="Mock page + token backend for embedding the AutoDrive Chatbot widget.",
    version="0.1.0",
)


def _widget_config(settings: Settings, base_url: str = "") -> dict[str, Any]:
    """Public config handed to the browser. Never includes the client secret.

    With ``autodrive_dev_proxy`` on, the widget is pointed at this backend's
    ``/autodrive-api`` prefix instead of the Assistant API, so browser calls
    stay same-origin (no CORS allow-listing needed for local simulation).
    """
    autodrive_url = settings.autodrive_url
    if settings.autodrive_dev_proxy and base_url:
        autodrive_url = f"{base_url.rstrip('/')}/autodrive-api"
    config: dict[str, Any] = {
        "container": "#autodrive-chat",
        "client": settings.autodrive_client,
        "apiProfile": settings.autodrive_api_profile,
        "datasetId": settings.autodrive_dataset_id,
        "environment": settings.autodrive_environment,
        "tokenEndpoint": settings.autodrive_token_endpoint,
        "autodriveUrl": autodrive_url,
        "locale": settings.autodrive_locale,
        "externalUserId": settings.mock_external_user_id,
        "title": settings.autodrive_title,
        "placeholder": settings.autodrive_placeholder,
        "theme": {
            "position": settings.autodrive_position,
            "primaryColor": settings.autodrive_primary_color,
            "accentColor": settings.autodrive_accent_color,
            "launcherLabel": settings.autodrive_launcher_label,
        },
    }
    # assistantId is only meaningful in assistant mode; omit it for embed mode.
    if settings.autodrive_api_profile == "assistant":
        config["assistantId"] = settings.autodrive_assistant_id
    return config


def _missing_required(settings: Settings) -> list[str]:
    """Required env vars that are still unset, for the page's setup banner."""
    missing = []
    if not settings.autodrive_dataset_id:
        missing.append("AUTODRIVE_DATASET_ID")
    if settings.autodrive_api_profile == "assistant" and not settings.autodrive_assistant_id:
        missing.append("AUTODRIVE_ASSISTANT_ID")
    if not settings.autodrive_mock_token and not settings.has_credentials:
        if not settings.autodrive_auth_client_id:
            missing.append("AUTODRIVE_AUTH_CLIENT_ID")
        if not settings.autodrive_auth_client_secret:
            missing.append("AUTODRIVE_AUTH_CLIENT_SECRET")
    return missing


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, settings: Settings = Depends(get_settings)):
    """Mock host page with the widget embedded."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "widget_script_url": settings.widget_script_url,
            "widget_config": _widget_config(settings, str(request.base_url)),
            "missing_required": _missing_required(settings),
            "mock_token": settings.autodrive_mock_token,
            "token_endpoint": settings.autodrive_token_endpoint,
        },
    )


@app.get("/healthz")
async def healthz(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "mock_token": settings.autodrive_mock_token,
        "credentials_configured": settings.has_credentials,
        "missing_required": _missing_required(settings),
    }


@app.get("/api/autodrive/config")
async def public_config(request: Request, settings: Settings = Depends(get_settings)):
    """The exact widget config this host renders — handy for debugging."""
    return _widget_config(settings, str(request.base_url))


def _authenticate(request: Request) -> str:
    """Stand-in for this host's own session check.

    A real integration validates the logged-in session here and derives the
    user identity from it instead of trusting anything from the browser.
    """
    return request.headers.get("X-Mock-User", "demo-user-1")


@app.post("/api/autodrive/chat-token")
async def chat_token(request: Request, settings: Settings = Depends(get_settings)):
    """Exchange server-side credentials for a short-lived widget token."""
    user_id = _authenticate(request)

    if settings.autodrive_mock_token:
        logger.info("Issuing mock token for user %s", user_id)
        return {
            "access_token": f"mock-access-token-for-{user_id}",
            "token_type": "Bearer",
            "expires_in": DEFAULT_EXPIRES_IN,
        }

    if not settings.has_credentials:
        raise HTTPException(
            status_code=500,
            detail=(
                "AUTODRIVE_AUTH_CLIENT_ID / AUTODRIVE_AUTH_CLIENT_SECRET are not set. "
                "Set them, or set AUTODRIVE_MOCK_TOKEN=true to demo without credentials."
            ),
        )

    try:
        async with httpx.AsyncClient(timeout=TOKEN_TIMEOUT_SECONDS) as client:
            upstream = await client.post(
                settings.token_url,
                headers={"Content-Type": "application/json"},
                json={
                    "clientId": settings.autodrive_auth_client_id,
                    "clientSecret": settings.autodrive_auth_client_secret,
                },
            )
    except httpx.HTTPError as exc:
        logger.error("Token exchange to %s failed: %s", settings.token_url, exc)
        raise HTTPException(
            status_code=502, detail=f"AutoDrive token exchange failed: {exc}"
        ) from exc

    if upstream.status_code >= 400:
        logger.error(
            "Token exchange rejected (%s): %s", upstream.status_code, upstream.text[:500]
        )
        return JSONResponse(
            status_code=502,
            content={
                "detail": "AutoDrive rejected the credentials.",
                "upstream_status": upstream.status_code,
            },
        )

    body = upstream.json()
    access_token = body.get("accessToken") or body.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=502, detail="AutoDrive response had no access token."
        )

    # /auth/token answers in camelCase; the widget contract is snake_case.
    return {
        "access_token": access_token,
        "token_type": body.get("tokenType") or body.get("token_type") or "Bearer",
        "expires_in": body.get("expiresIn")
        or body.get("expires_in")
        or DEFAULT_EXPIRES_IN,
    }


@app.api_route(
    "/autodrive-api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def autodrive_dev_proxy(
    path: str, request: Request, settings: Settings = Depends(get_settings)
):
    """Same-origin pass-through to the Assistant API (dev/simulation only).

    Browsers only reach the Assistant API directly when the page origin is in
    its CORS allow-list. This proxy keeps widget calls same-origin so the
    template works from any local port without Dadosfera-side changes.
    """
    if not settings.autodrive_dev_proxy:
        raise HTTPException(status_code=404, detail="Dev proxy is disabled.")

    upstream_url = f"{settings.autodrive_url.rstrip('/')}/{path}"
    # Forward only what the Assistant API needs; origin/cookies stay behind.
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "content-type", "accept"}
    }
    # The Assistant API enforces an allow-listed Origin/Referer on ai-question
    # even outside CORS preflight; present the simulated customer origin.
    if settings.autodrive_dev_proxy_origin:
        headers["Origin"] = settings.autodrive_dev_proxy_origin
    body = await request.body()
    # Compatibility shim (widget <-> API version mismatch): the published
    # widget sends orchestration.response_mode="auto" on ai-question, but the
    # deployed Assistant API only accepts generative|structured|hybrid and
    # 422s. Map "auto" -> "generative" until the widget/API are realigned.
    if request.method == "POST" and path.endswith("ai-question") and body:
        try:
            payload = json.loads(body)
            if payload.get("orchestration", {}).get("response_mode") == "auto":
                payload["orchestration"]["response_mode"] = "generative"
                body = json.dumps(payload).encode()
                logger.warning(
                    "Dev proxy shim: rewrote orchestration.response_mode auto->generative"
                )
        except (json.JSONDecodeError, AttributeError):
            pass

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream = await client.request(
                request.method,
                upstream_url,
                params=request.query_params,
                content=body,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        logger.error("Dev proxy request to %s failed: %s", upstream_url, exc)
        raise HTTPException(
            status_code=502, detail=f"Dev proxy request failed: {exc}"
        ) from exc

    return JSONResponse(
        status_code=upstream.status_code,
        content=upstream.json() if upstream.content else None,
    )


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":
    main()
