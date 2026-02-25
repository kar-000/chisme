# chisme 💬

> Retro IRC-style chat with a warm CRT aesthetic.
> FastAPI + PostgreSQL + Redis backend · React + Tailwind PWA frontend · WebSocket real-time messaging · WebRTC voice chat.

---

## Features

- **Real-time messaging** — server-scoped WebSocket with per-channel routing, typing indicators, and presence
- **Voice chat** — WebRTC peer-to-peer audio/video via a persistent global voice WebSocket
- **Direct messages** — 1-to-1 DM threads with unread badges and background notifications
- **Reactions** — Twemoji emoji reactions on messages
- **Polls** — single or multi-choice polls embedded in messages
- **Bookmarks** — save messages with optional notes
- **Reminders** — schedule a reminder on any message
- **Keyword alerts** — get notified when custom keywords appear in any channel
- **Quiet hours** — suppress notifications on a schedule
- **Channel notes** — collaborative per-channel scratchpad with version history
- **Message search** — full-text search with filters (user, channel, date, has-link, has-file)
- **GIF search** — Tenor integration
- **File uploads** — images (with thumbnails), attachments, and voice recordings
- **PWA** — installable, service-worker cached, Web Push notifications (VAPID)
- **Invites** — shareable invite codes with optional max-uses and expiry
- **Roles** — owner / admin / member per server
- **Operator dashboard** — site-admin controls (suspend servers, disable accounts)

---

## Quick Start (Docker)

```bash
cp backend/.env.example backend/.env
# Required: set SECRET_KEY (32+ random chars)
# Optional: TENOR_API_KEY, VAPID_* keys for GIF search / push notifications

docker compose up --build
```

| Service | URL |
|---------|-----|
| App | `http://localhost` |
| API docs (Swagger) | `http://localhost/docs` |
| Backend direct | `http://localhost:8000` |

---

## Development (local)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # fill in DATABASE_URL, SECRET_KEY, REDIS_URL

alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

### Tests

```bash
cd backend
pytest
```

---

## Configuration

Key environment variables (see `backend/.env.example` for the full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret (32+ chars) |
| `REDIS_URL` | Yes | Redis connection string |
| `SERVER_DOMAIN` | Yes | Public domain — used as identity namespace |
| `DOMAIN` | Yes | Deployment domain for Caddy TLS |
| `CORS_ORIGINS` | Yes | JSON array of allowed origins |
| `TENOR_API_KEY` | No | Enables GIF search |
| `VAPID_PRIVATE_KEY` | No | Enables Web Push notifications |
| `VAPID_PUBLIC_KEY` | No | Enables Web Push notifications |
| `VAPID_CLAIMS_EMAIL` | No | Contact email for push claims |

---

## API Overview

Full interactive docs at `/docs` (Swagger UI). Abbreviated reference below:

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout + revoke refresh token |
| GET  | `/api/auth/me` | Current user |

### Servers & Channels
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/servers` | List / create servers |
| PATCH/DELETE | `/api/servers/{id}` | Update / delete server |
| GET/POST | `/api/servers/{id}/channels` | List / create channels |
| POST | `/api/servers/{id}/channels/{id}/messages` | Send message |
| GET  | `/api/servers/{id}/channels/{id}/messages` | Message history |
| POST | `/api/servers/{id}/channels/{id}/read` | Mark channel read |

### Messages
| Method | Path | Description |
|--------|------|-------------|
| PUT | `/api/messages/{id}` | Edit message (24 h window) |
| DELETE | `/api/messages/{id}` | Soft-delete message |
| POST | `/api/messages/{id}/reactions` | Add reaction |
| DELETE | `/api/messages/{id}/reactions/{emoji}` | Remove reaction |

### Direct Messages
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/dms` | List / get-or-create DM channel |
| GET/POST | `/api/dms/{id}/messages` | DM history / send |

### Other endpoints
`/api/invites`, `/api/polls`, `/api/bookmarks`, `/api/reminders`,
`/api/search/messages`, `/api/upload`, `/api/gifs/search`,
`/api/users/me/keywords`, `/api/users/me/quiet-hours`,
`/api/channels/{id}/notes`, `/api/push/subscribe`, `/api/operator/*`

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `WS /ws/server/{server_id}` | Server-scoped: messages, typing, presence, voice counts |
| `WS /ws/voice` | Global voice signaling: WebRTC offer/answer/ICE, join/leave |
| `WS /ws/dm/{dm_id}` | DM channel: message delivery, typing indicators |

All WebSocket connections authenticate by sending `{"type": "auth", "token": "<jwt>"}` as the first message.

---

## Project Structure

```
chisme/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router mounts
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy engine & session
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # REST routers (auth, servers, channels, dms, …)
│   │   ├── core/                # Security helpers, JWT
│   │   ├── websocket/           # WS connection manager & handlers
│   │   ├── services/            # Push notifications, auth service
│   │   ├── redis/               # Redis key helpers, pub/sub
│   │   └── tests/               # pytest suite
│   ├── alembic/                 # Database migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # React UI components
│   │   │   ├── Auth/            # Login / register forms
│   │   │   ├── Chat/            # Messages, channels, DMs, polls, emoji picker
│   │   │   ├── Voice/           # Voice controls and participant display
│   │   │   ├── Server/          # Server list, icons, settings, invites
│   │   │   ├── Panels/          # Bookmarks, reminders, profile sidepanels
│   │   │   ├── Layout/          # Header, sidebar
│   │   │   └── Common/          # Shared UI primitives
│   │   ├── hooks/               # useWebSocket, useVoiceChat, useFaviconBadge, …
│   │   ├── store/               # Zustand stores (auth, chat, dm, bookmarks, …)
│   │   ├── services/            # Axios API client wrappers
│   │   ├── utils/               # Notifications, favicon badge, quiet hours
│   │   ├── pages/               # ChatLayout, OperatorDashboard
│   │   ├── App.jsx
│   │   └── sw.js                # Service worker (Workbox + push events)
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml           # db, redis, backend, frontend, caddy
└── Caddyfile                    # Reverse proxy + TLS config
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, SQLAlchemy 2, Alembic |
| Auth | PyJWT (HS256), bcrypt, opaque refresh tokens |
| Database | PostgreSQL 15 |
| Cache / pub-sub | Redis 7 |
| WebSocket | FastAPI WebSocket + Redis pub/sub fan-out |
| Voice | WebRTC (browser) + signaling over `/ws/voice` |
| Frontend | React 18, Vite, Tailwind CSS, Zustand |
| Emoji | emoji-mart + Twemoji |
| PWA | vite-plugin-pwa, Workbox, Web Push (VAPID) |
| Proxy | Caddy 2 (auto TLS) |
| Tests | pytest (backend), Vitest + Testing Library (frontend) |
