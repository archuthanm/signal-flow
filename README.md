# Market Monitor

Market Monitor is a free MVP for monitoring finance news across macro/rates, banking, and fintech. It ingests RSS feeds, scores stories for sector relevance, removes duplicates, stores articles in SQLite, generates rule-based summaries and "why it matters" notes, and outputs a markdown digest. A single-page FastAPI UI lets you run the pipeline and inspect the results from one screen.

## MVP scope

- professional-publication RSS sourcing via Google News queries
- 3 finance sectors: macro/rates, banking, fintech
- keyword-driven relevance scoring
- URL and title-based deduplication
- free rule-based enrichment instead of paid APIs
- SQLite persistence
- markdown digest generation
- single-page UI for review and future customization

## Project structure

```text
market_monitor/
├── app/
│   ├── collectors/
│   ├── filters/
│   ├── processors/
│   ├── reports/
│   ├── static/
│   ├── templates/
│   └── utils/
├── data/
├── output/
└── ...
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

Initialize the database:

```bash
python3 -m market_monitor.app.main init-db
```

Run the pipeline once:

```bash
python3 -m market_monitor.app.main run
```

Start the single-page UI:

```bash
python3 -m market_monitor.app.main serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` and use the page to run the pipeline, inspect stored articles, and refresh the digest.

## Deploy

The app is ready to deploy as a single FastAPI service.

Local production-style run:

```bash
uvicorn market_monitor.app.main:app --host 0.0.0.0 --port 8000
```

The repo includes a `Procfile`:

```text
web: uvicorn market_monitor.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Notes:

- static assets are served from `market_monitor/app/static/`
- templates are in `market_monitor/app/templates/`
- SQLite is fine for local use and lightweight demos
- for hosted deployment, use a persistent disk or switch to Postgres later if needed

## Commands

- `python3 -m market_monitor.app.main init-db`
- `python3 -m market_monitor.app.main ingest`
- `python3 -m market_monitor.app.main digest`
- `python3 -m market_monitor.app.main run`
- `python3 -m market_monitor.app.main serve`

## How relevance works

- `+3` for sector keyword hit in the title
- `+2` for sector keyword hit in the description
- `+1` for sector keyword hit in content
- `+1` if multiple finance terms appear
- trusted-source bonus for Reuters, FT, CNBC, MarketWatch, Yahoo Finance, and Nasdaq
- hard exclusions for crypto, personal finance, and retail-investing style noise

## How summaries work

This MVP does not use paid AI APIs. Instead it:

- extracts the most informative sentences from title/description/content
- builds a short factual summary
- generates a templated "why it matters" explanation
- derives tags from matched keywords and finance terms

The summariser is modular, so you can swap in a local LLM or API-based summariser later.

## Daily digest output

The markdown digest includes:

- top stories overall
- article counts by sector
- top articles for each target sector
- recurring themes inferred from tags

The generated digest is written to `output/daily_digest_<date>.md`.

## Tests

```bash
pytest
```

## Portfolio framing

Problem: finance news is high-volume and noisy.

Solution: this project ingests market articles from multiple sources, filters them by sector relevance, removes duplicate stories, stores the structured output, and produces a concise daily digest for quick market awareness.

Result: a reusable intelligence pipeline that demonstrates automation design, relevance logic, storage, reporting, and product-minded scoping.
