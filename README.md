# Open-Source Discovery Hub (OSDH)

> A self-hostable, open-source platform for discovering useful tools, libraries, apps, and learning resources. Focused on GitHub and trusted open-source sources, with local AI for summarization, tagging, and classification.

## The Problem

Finding useful, well-maintained open-source projects is harder than it should be. Search results are noisy, trending lists favor hype over quality, and there is no single place to discover projects by domain, language, or maintenance status.

## The Solution

OSDH aggregates open-source projects from multiple sources, uses local AI to summarize and classify them, and presents everything through a clean, offline-capable web UI and CLI. No API keys required. No cloud dependencies. Fully forkable.

## Features

### Source Aggregation
- **GitHub Repos** - Search by query, language, or topics via GitHub API
- **Awesome Lists** - Auto-discovered from [sindresorhus/awesome](https://github.com/sindresorhus/awesome) plus curated list
- **Educational Resources** - Learning paths, free books, algorithm repositories
- **Certificate Lists** - Cybersecurity and IT certification resources

### Local AI (via Ollama)
- **README Summarization** - Concise, factual, neutral summaries (2-4 sentences)
- **Tag Extraction** - Domain, language, platform, and use-case tags
- **Maintenance Classification** - Hybrid AI + rules (active, maintained, stale, archived)
- **Duplicate Detection** - Semantic comparison to find near-duplicate projects

### AI Rules

| Allowed | Forbidden |
|---------|-----------|
| Summarize READMEs factually | Ranking by "best" or "popular" |
| Extract keyword tags | Giving recommendations or advice |
| Classify maintenance status | Inventing facts |
| Detect duplicates | Opinions or preferences |

### Search & Filtering
- Full-text search across names, descriptions, and AI summaries
- Filter by language, license, source type, maintenance status, tags
- Sort by stars, last updated, name, or created date
- Grid and list view modes
- Page-based and infinite scroll pagination

### Snapshots & Export
- Versioned static datasets for offline use
- Export formats: **JSON**, **CSV**, **SQLite**
- Download or load snapshots back into the database

### Interfaces
- **Web UI** - Dark theme, responsive, offline-capable
- **CLI** - Full feature parity with the web UI

## Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) with the `phi3` model (for AI features)

### Option 1: Install Script

**Linux/macOS:**
```bash
./install.sh
source .venv/bin/activate
python main.py
```

**Windows (PowerShell):**
```powershell
.\install.ps1
.\.venv\Scripts\Activate.ps1
python main.py
```

### Option 2: Manual Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
cp .env.example .env
python main.py
```

### Option 3: Docker
```bash
# Make sure Ollama is running on your host first
ollama pull phi3

docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

## Usage

### Web UI

1. **Aggregate sources** - Click "Aggregate GitHub", "Aggregate Awesome", "Aggregate Education", or "Aggregate All" in the sidebar
2. **Search & filter** - Use the search bar and sidebar filters to find projects
3. **View details** - Click any project card to see the AI summary, tags, and metadata
4. **Create snapshots** - Click "Create Snapshot" to export your database

### CLI

```bash
# Search resources
python cli.py search -q "web scraping" -l python --limit 10

# Get detailed info
python cli.py info github-123456

# Aggregate sources
python cli.py aggregate --source github -q "machine learning" -l python
python cli.py aggregate --source awesome
python cli.py aggregate --source educational
python cli.py aggregate --source all

# Run AI processing manually
python cli.py ai-process

# Create snapshots
python cli.py snapshot --format all
python cli.py snapshots-list

# View statistics
python cli.py stats

# View aggregation logs
python cli.py logs

# JSON output for scripting
python cli.py search -q "api" --json-output
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
# Server
OSDH_ENV=development
OSDH_HOST=0.0.0.0
OSDH_PORT=8080

# Database & Storage
OSDH_DB_PATH=./data/osdh.db
OSDH_SNAPSHOT_DIR=./data/snapshots
OSDH_CACHE_DIR=./data/cache

# Ollama AI
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3
OLLAMA_TIMEOUT=120

# GitHub (optional - increases rate limits)
GITHUB_API_TOKEN=
GITHUB_RATE_LIMIT_DELAY=2.0

# Logging
LOG_LEVEL=INFO
```

## Project Structure

```
OSDH/
├── main.py                    # Entry point
├── cli.py                     # CLI tool
├── requirements.txt           # Python dependencies
├── .env.example               # Configuration template
├── Dockerfile                 # Container image
├── docker-compose.yml         # Docker Compose setup
├── install.sh                 # Bash installer
├── install.ps1                # PowerShell installer
│
├── app/
│   ├── config.py              # Application settings
│   ├── db.py                  # SQLAlchemy models & database
│   │
│   ├── cache/
│   │   └── file_cache.py      # Disk cache for READMEs (7d) & AI results (30d)
│   │
│   ├── aggregators/
│   │   ├── github.py          # GitHub API search & fetch
│   │   ├── awesome.py         # Auto-discover + curated Awesome lists
│   │   └── educational.py     # Educational & certification resources
│   │
│   ├── ai/
│   │   └── ollama.py          # Ollama client (summarize, tag, classify, dedupe)
│   │
│   ├── api/
│   │   ├── __init__.py        # FastAPI app setup
│   │   ├── routes.py          # Search, filter, stats endpoints
│   │   ├── aggregate.py       # Aggregation trigger endpoints
│   │   ├── snapshots.py       # Snapshot CRUD & download
│   │   └── schemas.py         # Pydantic models
│   │
│   └── snapshots/
│       └── manager.py         # JSON/CSV/SQLite export logic
│
└── static/
    ├── index.html             # Web UI
    ├── css/style.css          # Dark theme styles
    └── js/app.js              # Frontend logic
```

## AI Model

The default model is **phi3** - lightweight and suitable for most hardware:

| Model | RAM Required | Speed | Quality |
|-------|-------------|-------|---------|
| phi3 | ~2 GB | Fast | Good |
| llama3.2 | ~4 GB | Medium | Better |
| llama3.1:8b | ~8 GB | Slower | Best |

Change the model in `.env`:
```env
OLLAMA_MODEL=llama3.2
```

## Maintenance Classification

Uses a hybrid approach for efficiency:

| Rule | Classification |
|------|---------------|
| `is_archived` flag set | `archived` |
| Last commit <= 30 days ago | `active` |
| Last commit > 365 days ago | `stale` |
| Everything else | AI classified |

## Caching

- **READMEs**: Cached for 7 days to avoid re-fetching
- **AI results**: Cached for 30 days to avoid re-processing
- Cache stored in `./data/cache/` and safe to delete

## Offline Usage

1. Aggregate your sources while online
2. Run AI processing to generate summaries and tags
3. Create a snapshot: `python cli.py snapshot --format all`
4. The web UI works offline with the local SQLite database

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/resources` | Search & filter resources |
| GET | `/api/resources/{id}` | Get single resource |
| GET | `/api/stats` | Database statistics |
| GET | `/api/filters` | Available filter options |
| POST | `/api/aggregate/run` | Run aggregation |
| GET | `/api/aggregate/logs` | View aggregation logs |
| POST | `/api/aggregate/ai-process` | Run AI processing |
| POST | `/api/snapshots/create` | Create snapshot export |
| GET | `/api/snapshots/list` | List available snapshots |
| GET | `/api/snapshots/download/{id}/{type}` | Download snapshot |

## License

MIT
