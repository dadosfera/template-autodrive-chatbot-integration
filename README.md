# AutoDrive Chatbot Integration — Mock Host

> **Autodrive DDF — repo-group**
> - **This repo:** reference host for embedding the Autodrive chatbot widget (mock page + token backend).
> - **Role in the group:** integration template for customer sites.
> - **Status:** template.
> - **Group map:** [dadosfera/autodrive-ddf-group](https://github.com/dadosfera/autodrive-ddf-group)

A runnable reference integration of the **AutoDrive Chatbot widget**, following
the [official installation guide](https://autodrive-verticity.stg.dadosfera.ai/help/how-to/chatbot).

It stands in for a customer site and provides the two pieces any host app needs:

| Piece | Where | What it does |
| --- | --- | --- |
| Mock HTML page | [src/templates/index.html](src/templates/index.html) | Embeds the widget via `window.AutoDriveChat.init(...)`, shows the live config, logs widget events, and exposes a "simulate logout" button wired to `resetConversation()`. |
| Token backend | [src/main.py](src/main.py) | Serves `POST /api/autodrive/chat-token` — the widget's `tokenEndpoint`. Exchanges the server-side credentials for a short-lived token and converts the Assistant API's camelCase response into the widget's snake_case contract. |

The client secret lives only on the server. The page config is rendered
server-side and never contains it — enforced by a test.

---

## Quick start

```bash
cp .env.example .env      # already prefilled with the Verticity STG values
# add AUTODRIVE_AUTH_CLIENT_ID and AUTODRIVE_AUTH_CLIENT_SECRET, then:
docker compose up --build
```

Open <http://localhost:8000>. To see the page mount without credentials, set
`AUTODRIVE_MOCK_TOKEN=true` — the token endpoint then returns a synthetic token
(the widget mounts, but real answers still require real credentials).

```bash
docker compose run --rm tests     # 15 tests, run inside the container
docker compose down               # stop
```

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Mock host page with the widget embedded |
| `POST` | `/api/autodrive/chat-token` | The widget's `tokenEndpoint` |
| `GET` | `/api/autodrive/config` | The exact widget config being rendered (debugging) |
| `GET` | `/healthz` | Health + which required variables are still unset |

---

## Environment configuration

Everything is driven by env vars — see [.env.example](.env.example). **`.env` is
gitignored; never commit real credentials.**

### 1. Credentials (server-side only, never in page HTML/JS)

| Variable | Notes |
| --- | --- |
| `AUTODRIVE_AUTH_CLIENT_ID` | Client identifier for the token exchange. |
| `AUTODRIVE_AUTH_CLIENT_SECRET` | Client secret. Env var or secret manager only. |

For Verticity STG these live in the `autodrive-secrets` Kubernetes secret,
namespace `autodrive-verticity` on the `platform-stg` cluster (VPN required):

```bash
kubectl --context platform-stg -n autodrive-verticity \
  get secret autodrive-secrets -o jsonpath='{.data.AUTODRIVE_AUTH_CLIENT_ID}' | base64 -d
```

They are already populated in the local (gitignored) `.env`.

### CORS — required before the widget works from localhost

The Assistant API validates the request `Origin` both in CORS preflight **and**
server-side (a disallowed origin gets `403 "Origem da requisição não
permitida."`, even with a valid token). The STG allowlist is currently:

```
ASSISTANT_API_CORS_ALLOW_ORIGINS =
  https://autodrive-verticity.stg.dadosfera.ai,
  https://build.verticity.com:8004
```

`http://localhost:8080` is **not** in it, so the widget on this mock host will
be blocked in the browser. Your exact origin including port must be added to
that variable on the `autodrive-assistant-api` deployment in the
`autodrive-verticity` namespace.

### 2. Already filled in from the Verticity scenario

| Variable | Value |
| --- | --- |
| `AUTODRIVE_CLIENT` | `verticity` |
| `AUTODRIVE_URL` | `https://autodrive-assistant-api-verticity.stg.dadosfera.ai` |
| `AUTODRIVE_DATASET_ID` | `21225fd5-b523-466c-8f5d-548b8b059d3f` (DSL) |
| `AUTODRIVE_ASSISTANT_ID` | `67d07db4-5eb0-430e-ac64-ff1ac63836f4` (Business) — Technical is `db739c3d-74bf-40f3-839b-984a0df25739` |
| `AUTODRIVE_API_PROFILE` | `assistant` |
| `AUTODRIVE_ENVIRONMENT` | `stg` |
| `AUTODRIVE_TOKEN_ENDPOINT` | `/api/autodrive/chat-token` |
| `AUTODRIVE_WIDGET_HOST` | `https://autodrive-verticity.stg.dadosfera.ai` (serves the bundle) |

> `AUTODRIVE_URL` must be the **Assistant API** host, never your own site's
> host — the widget builds `{AUTODRIVE_URL}/datasets/{datasetId}/ai-question`
> from it and will otherwise 404.

### 3. Optional

| Variable | Default | Notes |
| --- | --- | --- |
| `AUTODRIVE_LOCALE` | `en-US` | `pt-BR` (widget default), `en-US`, `es-ES`. Unsupported values fall back to `pt-BR`. |
| `AUTODRIVE_TITLE` | `AutoDrive Assistant` | Header text. |
| `AUTODRIVE_PLACEHOLDER` | `Type your question...` | Input placeholder. |
| `AUTODRIVE_POSITION` | `bottom-right` | `bottom-right`, `bottom-left`, `inline`. |
| `AUTODRIVE_PRIMARY_COLOR` | `#111827` | Theme. |
| `AUTODRIVE_ACCENT_COLOR` | `#2563EB` | Theme. |
| `AUTODRIVE_LAUNCHER_LABEL` | `Open assistant` | Launcher button label. |
| `AUTODRIVE_MOCK_TOKEN` | `false` | `true` → synthetic token, no Assistant API call. Demo only. |
| `MOCK_EXTERNAL_USER_ID` | `demo-user-1` | Stands in for the logged-in user; sent as `externalUserId`. |
| `PORT` | `8000` | Host port published by compose. |

---

## Notes for a real integration

Two things this mock deliberately fakes — replace them before shipping:

- **`externalUserId`** comes from `MOCK_EXTERNAL_USER_ID` here. In production,
  derive it from the authenticated session server-side. AutoDrive scopes
  conversations to this value, so a `conversation_id` created by one user can
  never be read or continued by another. It is required for multi-user sites,
  and it also keeps the conversation alive across reloads in the same tab.
- **Session validation** in `_authenticate()` ([src/main.py](src/main.py)) trusts
  an `X-Mock-User` header. A real token endpoint must validate the logged-in
  session and never trust browser-supplied identity.

Tokens expire in ~5 minutes; the widget renews automatically on `401`. Wire
`resetConversation()` into your logout flow so the next user starts fresh.

## Layout

```
src/main.py               FastAPI app: page + token endpoint
src/config.py             Env-driven settings
src/templates/index.html  Mock host page with the widget
tests/                    15 tests: token contract, secret isolation, config modes
Dockerfile                Python 3.11 slim image
docker-compose.yml        `web` service + `tests` profile
.env.example              Every variable, documented
```
