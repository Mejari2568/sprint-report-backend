# Sprint Report Generator

Upload your Jira Excel export → get a professional sprint report in seconds.

## Architecture

```
frontend/index.html  →  GitHub Pages  (public URL)
backend/app.py       →  Render.com    (API key stored securely)
```

---

## Deploy Backend (Render) — 5 minutes

1. Create a new GitHub repo called `sprint-report-backend`
2. Push the contents of the `backend/` folder to it
3. Go to [render.com](https://render.com) → New → Web Service
4. Connect your GitHub repo
5. Render auto-detects `render.yaml` — just confirm settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
6. Add environment variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: your key from [console.anthropic.com](https://console.anthropic.com)
7. Click **Deploy** — your API URL will be: `https://sprint-report-api.onrender.com`

> Render free tier spins down after inactivity. First request after sleep takes ~30s.

---

## Deploy Frontend (GitHub Pages) — 2 minutes

1. Create a new GitHub repo called `sprint-report` (or any name)
2. Push the contents of the `frontend/` folder to it
3. Go to repo **Settings → Pages → Branch: main → Save**
4. Your app is live at: `https://yourusername.github.io/sprint-report`

---

## Using the App

1. Open your GitHub Pages URL
2. Paste your Render backend URL in the field at the top → click **ping** to verify
3. Drop your Jira Excel export
4. Fill sprint details (name, dates, team, goal)
5. Select report sections
6. Click **Generate sprint report**
7. Download as HTML or Print → Save as PDF

---

## Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
# runs on http://localhost:5000

# Frontend — just open in browser
open frontend/index.html
# set backend URL to http://localhost:5000
```

---

## API Reference

### `GET /`
Health check — returns `{"status": "ok"}`

### `POST /generate-report`
```json
{
  "sprint": "Sprint 23",
  "dates": "Apr 21 – May 2",
  "team": "Phoenix Squad",
  "scrum_master": "Jane Doe",
  "goal": "Ship payments v2",
  "notes": "Any extra context",
  "sections": ["executive", "velocity", "assignee", "bugs", "epics", "incomplete"],
  "tickets": [
    {
      "summary": "User login flow",
      "status": "Done",
      "type": "Story",
      "points": 5,
      "assignee": "Alice",
      "epic": "User Management",
      "priority": "High"
    }
  ]
}
```

Response:
```json
{
  "success": true,
  "html": "<h1>Sprint 23 Report</h1>..."
}
```
