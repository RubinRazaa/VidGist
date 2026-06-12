import os
import glob
import time
import asyncio
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import yt_dlp
from google import genai
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MODEL = "gemini-2.5-flash"

PROMPT = """ou are analyzing a short Instagram reel for a written business record.
Watch and listen to the whole video, INCLUDING any on-screen text, captions, and graphics.

Respond in English using EXACTLY this structure:

Title: <short descriptive title for the reel>

Translation (English – Exact):
"<a faithful, complete English transcription of everything spoken in the video, in order.
If the video is not in English, translate it exactly. Weave in important on-screen text.
Keep the speaker's wording — do not paraphrase, shorten, or skip parts.>"

Summary:
<2–4 sentences: what the video is about and its main message>

Useful for the company?: <Yes/No> (<category, e.g. Strategic / Technical / Marketing / Governance & Risk>).
<one sentence on why it is or is not useful for a business>

Departments that benefit:
* <Department> – <how it benefits>
<3–6 bullets; write "None" if not useful>

Key Insight:
* <takeaway>
<4–7 short bullets with the most important takeaways>

Rules:
- Base everything ONLY on the video. Do NOT add outside information or fact-check claims — report what the video says.
- If a part is inaudible or unclear, write [unclear] instead of guessing.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY or API_KEY == "PASTE_YOUR_KEY_HERE" or API_KEY == "your_key_here":
    raise SystemExit(
        "\n"
        "  ┌──────────────────────────────────────────────────────────────┐\n"
        "  │  No Gemini API key found.                                     │\n"
        "  └──────────────────────────────────────────────────────────────┘\n"
        "\n"
        "  This app needs a (free) Google Gemini key to read reels.\n"
        "\n"
        "  1. Get one here:   https://aistudio.google.com/apikey\n"
        "  2. Copy the template:   cp .env.example .env\n"
        "  3. Open .env and set:   GEMINI_API_KEY=your_real_key\n"
        "  4. Start the server again.\n"
        "\n"
        "  (The .env file lives in the project root and is never committed.)\n"
    )
client = genai.Client(api_key=API_KEY)


def download_reel(url, out_dir):
    ydl_opts = {
        "outtmpl": os.path.join(out_dir, "reel.%(ext)s"),
        "format": "best[ext=mp4]/best/bestvideo+bestaudio",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    files = glob.glob(os.path.join(out_dir, "reel.*"))
    if not files:
        raise RuntimeError("Download produced no file.")
    return files[0]


def analyze(video_path):
    video_file = client.files.upload(file=video_path)

    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError("Gemini could not process this video.")

    response = _generate_with_retry([video_file, PROMPT])

    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return response.text


def _generate_with_retry(contents, attempts=4):
    delay = 2
    last_err = None
    for i in range(attempts):
        try:
            return client.models.generate_content(model=MODEL, contents=contents)
        except Exception as e:
            msg = str(e)
            transient = (
                "503" in msg
                or "UNAVAILABLE" in msg
                or "overloaded" in msg.lower()
                or "high demand" in msg.lower()
                or "429" in msg
                or "RESOURCE_EXHAUSTED" in msg
            )
            if not transient or i == attempts - 1:
                raise
            last_err = e
            time.sleep(delay)
            delay *= 2
    raise last_err


def explain_url(url):
    with tempfile.TemporaryDirectory() as tmp:
        path = download_reel(url, tmp)
        return analyze(path)


app = FastAPI(title="VidGist")

ALLOWED_ORIGINS = os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExplainRequest(BaseModel):
    url: str


@app.post("/api/explain")
async def api_explain(req: ExplainRequest):
    url = (req.url or "").strip()
    if "instagram.com" not in url:
        return JSONResponse(
            status_code=400,
            content={"error": "Paste a valid Instagram reel URL (it should contain instagram.com)."},
        )
    try:
        explanation = await asyncio.to_thread(explain_url, url)
        return {"explanation": explanation}
    except Exception as e:
        msg = str(e)
        low = msg.lower()
        if any(s in msg for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")) \
                or "high demand" in low or "overloaded" in low:
            hint = (
                "Gemini is busy right now (we already retried a few times). "
                "Give it a minute and try again."
            )
        elif "login" in low or "forbidden" in low or "rate-limit" in low or "private" in low:
            hint = (
                "This reel needs a logged-in session. Add a "
                "cookiesfrombrowser entry to ydl_opts in reels.py pointing to a "
                "browser where you're logged into Instagram."
            )
        else:
            hint = "If downloads stopped working in general, update the downloader: pip install -U yt-dlp"
        return JSONResponse(
            status_code=500,
            content={"error": msg, "hint": hint},
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
