# Italian Lens

A personal learning companion: point your phone's camera at Italian text in daily life
(menus, signs, shelf labels, receipts, notices) and it extracts and translates the useful
text, and builds a personal vocabulary database from what you actually encounter — for
you to review later.

Runs fully offline (no API key, no per-photo cost) using local OCR, translation, and NLP
models. The trade-off: no AI scene understanding, and translation/vocabulary picking are
more mechanical than a vision model would give you — see [How it works](#how-it-works).

## How it works

- **Capture** — take a photo on your phone (native camera, via the file input's
  `capture="environment"` attribute — no live video stream needed).
- **OCR** — [Tesseract](https://github.com/tesseract-ocr/tesseract) reads the Italian text
  out of the photo, locally.
- **Translate** — [Argos Translate](https://github.com/argosopentech/argos-translate)
  translates each line of text to English, fully offline (after a one-time model download
  on first use).
- **Vocabulary** — [spaCy](https://spacy.io/)'s Italian model tags each word's part of
  speech and picks out content words (nouns, verbs, adjectives, adverbs) as vocabulary
  candidates, using the actual line they appeared in as the example sentence.
- **Save** — everything is stored in a local SQLite database (`data/italian_lens.db`).
  Repeated words are tracked (`times_seen`) instead of duplicated.
- **Review** — browse your growing vocabulary list (tap a card to reveal the English) or
  your capture history (photo + what was found).

Since there's no vision model, there's no scene description ("a trattoria menu board") —
just the extracted text. Translation is literal/word-for-word rather than context-aware,
and vocabulary is picked by grammar rules rather than judgment about what's actually
useful, so expect some noise (mistagged words, awkward phrasing).

## Setup

1. Install [Homebrew](https://brew.sh) if you don't have it, then install Tesseract with
   language data (this app was set up with `tesseract-lang`, which includes Italian):
   ```bash
   brew install tesseract tesseract-lang
   ```
2. Install Python dependencies (a virtualenv `.venv` is already set up in this folder):
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Download the Italian spaCy model (one-time):
   ```bash
   python -m spacy download it_core_news_sm
   ```
4. Run the server:
   ```bash
   python app.py
   ```
   It listens on `http://0.0.0.0:5420`. The first photo you analyze will download the
   Argos Translate Italian→English model (needs internet, one time); everything after
   that runs offline.

## Using it on your phone

The server binds to all interfaces, so on the same WiFi network you can open it from
your phone at `http://<your-computer's-LAN-IP>:5420`. Find your LAN IP with:

```bash
ipconfig getifaddr en0
```

Note: this only works while your phone and computer share the same WiFi network. Because
the whole pipeline runs locally with no external API calls, this app is a good candidate
to deploy to a small always-on host (or even run on a Raspberry Pi) so it works over
mobile data in Italy — that's a deployment step for later, not a code change.

## Project layout

- `app.py` — Flask routes (serve frontend, analyze photo, list/query captures & vocabulary)
- `extract.py` — the OCR → translate → vocabulary-tagging pipeline
- `db.py` — SQLite schema and queries
- `static/` — the mobile frontend (capture / review / history tabs)
- `data/` — SQLite DB + uploaded photos (gitignored, created at runtime)
