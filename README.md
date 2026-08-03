# Italian Lens

A personal learning companion: point your phone's camera at Italian text in daily life
(menus, signs, shelf labels, receipts, notices) and it understands the scene, extracts
and translates the useful text, and builds a personal vocabulary database from what you
actually encounter — for you to review later.

## How it works

- **Capture** — take a photo on your phone (native camera, via the file input's
  `capture="environment"` attribute — no live video stream needed).
- **Analyze** — the photo is sent to Claude's vision API, which describes the scene,
  extracts the useful Italian text with translations, and picks out vocabulary worth
  learning (word, meaning, part of speech, example sentence).
- **Save** — everything is stored in a local SQLite database (`data/italian_lens.db`).
  Repeated words are tracked (`times_seen`) instead of duplicated.
- **Review** — browse your growing vocabulary list (tap a card to reveal the English) or
  your capture history (photo + what was found).

## Setup

1. Get an Anthropic API key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).
2. Copy `.env.example` to `.env` and paste your key in:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies (a virtualenv `.venv` is already set up in this folder):
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python app.py
   ```
   It listens on `http://0.0.0.0:5420`.

## Using it on your phone

The server binds to all interfaces, so on the same WiFi network you can open it from
your phone at `http://<your-computer's-LAN-IP>:5420`. Find your LAN IP with:

```bash
ipconfig getifaddr en0
```

Note: this only works while your phone and computer share the same WiFi network. To use
it out and about in Italy on mobile data, you'll need to deploy it to a host with
persistent storage (e.g. Render, Fly.io, a small VPS) — the app has no hard dependency on
localhost, so this is a deployment step for later, not a code change.

## Project layout

- `app.py` — Flask routes (serve frontend, analyze photo, list/query captures & vocabulary)
- `vision.py` — the Claude vision call and its structured-output schema
- `db.py` — SQLite schema and queries
- `static/` — the mobile frontend (capture / review / history tabs)
- `data/` — SQLite DB + uploaded photos (gitignored, created at runtime)
