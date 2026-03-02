# CrisisVerify — Deployment Guide

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- (Optional) Gemini API key
- (Optional) Serper.dev API key

---

## Docker Compose (Recommended)

```bash
git clone https://github.com/your-org/crisisverify.git
cd crisisverify

# Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env to add API keys

# Build and start
docker-compose up --build

# Or in detached mode
docker-compose up -d --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Stop

```bash
docker-compose down
```

---

## Local Development (No Docker)

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # Add your API keys

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev           # http://localhost:3000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | No | `` | Google Gemini API key (LLM claim extraction) |
| `SERPER_API_KEY` | No | `` | Serper.dev search API key (evidence retrieval) |
| `RATE_LIMIT_PER_MINUTE` | No | `10` | Requests per minute per IP |

> The app runs in **full demo mode without any API keys**. Mock evidence and heuristic claim extraction will be used — suitable for demonstration purposes.

---

## Production Notes

- Place a reverse proxy (Nginx/Caddy) in front of both services.
- Set `NEXT_PUBLIC_API_URL` to your backend's public URL.
- Use Docker Compose `--restart unless-stopped` (already configured).
- Never commit `.env` files. Use secrets management in CI/CD.

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```
