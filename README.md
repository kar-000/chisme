# chisme 💬

> Retro IRC-style chat with a warm CRT aesthetic.
> FastAPI + PostgreSQL backend · React + Tailwind frontend · WebSocket real-time messaging.

---

## Quick Start (Docker)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY

docker compose up --build
```

Backend available at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

---

## Development (local)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Start Postgres (or use docker compose -f docker-compose.dev.yml up db)
cp .env.example .env             # fill in DATABASE_URL, SECRET_KEY

alembic upgrade head
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pytest
```

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET  | `/api/auth/me` | Current user |
| GET  | `/api/channels` | List channels |
| POST | `/api/channels` | Create channel |
| GET  | `/api/channels/{id}/messages` | Message history |
| POST | `/api/channels/{id}/messages` | Send message |
| PUT  | `/api/messages/{id}` | Edit message (24h window) |
| DELETE | `/api/messages/{id}` | Delete message (soft) |
| POST | `/api/messages/{id}/reactions` | Add reaction |
| DELETE | `/api/messages/{id}/reactions/{emoji}` | Remove reaction |
| WS   | `/ws/channels/{id}` | Real-time channel events |

Full interactive docs: `http://localhost:8000/docs`

---

## Color Palette (Warm CRT)

| Token | Hex | Use |
|-------|-----|-----|
| `--crt-teal` | `#00CED1` | Primary text, glow |
| `--crt-teal-light` | `#5DADE2` | Usernames, highlights |
| `--crt-pink` | `#FFB6C1` | Own messages |
| `--crt-orange` | `#FF8C42` | Unread badges |
| `--crt-gray` | `#8B8B8B` | Timestamps |
| `--crt-dark` | `#1a1612` | Background |

---

## Project Structure

```
chisme/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── database.py      # SQLAlchemy engine & session
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── api/             # REST endpoint routers
│   │   ├── core/            # Security, JWT, event constants
│   │   ├── websocket/       # WS connection manager & handlers
│   │   └── tests/           # pytest test suite (85%+ coverage)
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
└── docker-compose.dev.yml
```
