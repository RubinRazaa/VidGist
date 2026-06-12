# VidGist

Paste an Instagram reel link and get a clear, written explanation of it — the
spoken audio *and* the on-screen text — without watching it. The reel is read by
Google's Gemini and never stored.

## Structure

```
VidGist/
├── backend/
│   └── reels.py        FastAPI JSON API (download + Gemini)
├── web/                Next.js frontend (App Router + TypeScript)
├── requirements.txt    Python dependencies
├── .env                Your GEMINI_API_KEY (not committed)
└── .env.example        Template for .env
```

The frontend talks to the backend through a dev proxy (`/api/*` → port 8000),
so the browser only ever hits the Next.js origin.

## Setup (one time)

1. **Python deps**

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **API key** — copy the template and paste your key in:

   ```bash
   cp .env.example .env
   # then edit .env:  GEMINI_API_KEY=your_key_here
   ```

   Get a key at https://aistudio.google.com/apikey.

3. **Frontend deps**

   ```bash
   cd web && npm install
   ```

## Run (two terminals)

**Terminal 1 — backend** (from the project root):

```bash
.venv/bin/uvicorn backend.reels:app --reload --port 8000
```

**Terminal 2 — frontend**:

```bash
cd web && npm run dev
```

Then open **http://localhost:3000**.

## Notes

- **ffmpeg** is not required — the backend downloads reels as a single
  combined file. (Only needed for the rare reel served as separate streams.)
- If Gemini returns a 503 ("high demand"), the backend retries automatically
  with backoff. Sustained busy spells: wait a minute and retry.
- Private or rate-limited reels need a logged-in session: add a
  `cookiesfrombrowser` entry to `ydl_opts` in `backend/reels.py`.

## Requirements

- **Python 3.9+** and **Node.js 18+**
- A free **Gemini API key** (each user brings their own — it is never shared
  or committed). Get one at https://aistudio.google.com/apikey.

## Troubleshooting

**Backend won't start / "No Gemini API key found"**
You haven't set your key. Copy the template and paste your own key in:
```bash
cp .env.example .env
# edit .env →  GEMINI_API_KEY=your_real_key
```
The `.env` file must be in the **project root** (next to `requirements.txt`).

**"Couldn't reach the backend" in the web page**
The frontend (port 3000) is running but the backend (port 8000) isn't. Start it
in a second terminal:
```bash
.venv/bin/uvicorn backend.reels:app --reload --port 8000
```

**"high demand" / 503 error**
Gemini is temporarily overloaded. The backend already retries a few times — if
it still fails, wait a minute and try again.

**"ffmpeg is not installed" while downloading**
That specific reel is served as separate audio/video streams. Most reels are
not. Install ffmpeg if you hit it often (`brew install ffmpeg` on macOS).

**"login required" / "forbidden" / private reel**
The reel needs an Instagram session. In `backend/reels.py`, add a
`cookiesfrombrowser` entry to `ydl_opts` in `download_reel()`, e.g.
`"cookiesfrombrowser": ("firefox",)` (point it at a browser where you're logged
into Instagram — Firefox is the most reliable).

**Downloads suddenly stopped working**
Instagram changed something. Update the downloader:
```bash
.venv/bin/pip install -U yt-dlp
```
