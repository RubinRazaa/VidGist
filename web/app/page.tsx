"use client";

import { useState } from "react";

type Status = "idle" | "loading" | "done" | "error";

export default function Home() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    setStatus("loading");
    setText("");
    setCopied(false);

    try {
      const res = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: trimmed }),
      });

      const raw = await res.text();
      let data: { explanation?: string; error?: string; hint?: string } | null =
        null;
      try {
        data = JSON.parse(raw);
      } catch {
        setText(
          "Can't reach the backend right now. Make sure it's running:\n\n" +
            "    cd VidGist\n" +
            "    .venv/bin/uvicorn backend.reels:app --reload --port 8000"
        );
        setStatus("error");
        return;
      }

      if (!res.ok) {
        const msg =
          (data?.error ?? "Couldn't get through to it.") +
          (data?.hint ? `\n\n${data.hint}` : "");
        setText(msg);
        setStatus("error");
      } else {
        setText(data?.explanation ?? "Came back empty — try another link.");
        setStatus("done");
      }
    } catch (err) {
      setText(
        `Couldn't reach the server. ${
          err instanceof Error ? err.message : ""
        }`.trim()
      );
      setStatus("error");
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  }

  const loading = status === "loading";

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-inner">
          <span className="mark" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="6 4 20 12 6 20 6 4" />
            </svg>
          </span>
          <span className="wordmark">VidGist</span>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <h1>What&apos;s this video actually saying?</h1>
          <p className="lead">
            Drop in a link and you&apos;ll get a short write-up of what happens —
            the words spoken out loud and the text on screen, all in one place.
            No need to sit through it.
          </p>
        </section>

        <form className="form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste an Instagram or TikTok link"
            autoComplete="off"
            spellCheck={false}
            disabled={loading}
          />
          <button type="submit" className="primary" disabled={loading}>
            {loading && <span className="spinner" aria-hidden />}
            <span>{loading ? "Reading it" : "Break it down"}</span>
          </button>
        </form>
        <p className="note">
          Public videos just work. If it&apos;s private or really long, you might
          need to be logged in.
        </p>

        {status !== "idle" && (
          <div className={`result${status === "error" ? " result-error" : ""}`}>
            <div className="result-head">
              <span className="result-label">
                {status === "error" ? "That didn't go through" : "Here's the gist"}
              </span>
              {status === "done" && (
                <button type="button" className="copy" onClick={copy}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              )}
            </div>

            {loading ? (
              <div className="skeleton">
                <span /><span /><span /><span />
              </div>
            ) : (
              <div className="output">{text}</div>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        <div className="footer-inner">
          We pull the video down just long enough to read it, then it&apos;s gone.
          Nothing gets saved.
        </div>
      </footer>
    </div>
  );
}
