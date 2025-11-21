# SpecAlign

A comprehensive security analysis system for AI-assisted development that uses the Dev Spec Kit (extracted from claude-code) as a component, wrapped with additional guidance and a modern web interface.

## High-level Flow

```
Developer Prompt → Orchestrator → Dev Spec Kit checks + Custom guidance → Final Curated Prompt → Claude → Result
```

## Architecture

- **`dev-spec-kit/`** — Security and quality check engine (shell-based rules)
- **`spec-kit/`** — Optional: GitHub's spec-driven development workflow tool (additive layer)
- **`orchestrator/`** — Python orchestration layer (analyzes prompts, applies guidance)
- **`api/`** — FastAPI REST API (exposes analysis endpoints)
- **`ui/`** — React frontend (dark theme with before/after view)

> **Note:** spec-kit is an optional workflow tool that runs *before* security analysis when enabled via `USE_SPEC_KIT=true`. It is **additive** and never replaces dev-spec-kit security checks. See [SPEC_KIT_INTEGRATION.md](SPEC_KIT_INTEGRATION.md) for details.

## Quick Start

### Option 1: One-Command Startup (Recommended)

```bash
./scripts/start.sh
```

This will:
1. Start the backend API on `http://localhost:8000`
2. Start the frontend UI on `http://localhost:3000`
3. Open the UI in your browser

### Option 2: Manual Startup

**Start Backend:**
```bash
./scripts/server.sh start
# Or manually:
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
cd ui
npm install  # First time only
npm run dev
```

**Access:**
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Shutdown

```bash
./scripts/stop.sh
```

## Features

### Backend (FastAPI + Python)
- Dev-Spec-Kit Integration - Wraps shell-based security rules engine
- Guidance Engine - Generates additional security constraints
- Prompt Curation - Enhances prompts with security requirements
- REST API - Clean endpoints with OpenAPI documentation
- CLI Interface - Command-line tool for analysis

### Frontend (React + Dark Theme)
- Dark Theme - Sleek UI with warm accents
- Before/After View - Original prompt vs curated prompt
- Risk Level Indicator - High/Medium/Low visual badge
- Severity Grouping - Issues by BLOCKER/ERROR/WARNING/INFO
- Guidance Display - Actionable security recommendations
- Real-time Analysis - Instant feedback on prompt security

## Usage

### Web Interface

1. Open http://localhost:3000
2. Enter your developer prompt in the left panel
3. Click "Analyze Prompt" (or press Ctrl/Cmd + Enter)
4. View results in the right panel:
   - Risk level badge (High/Medium/Low)
   - Curated prompt with security constraints
   - Issues grouped by severity with colored labels
   - Additional guidance items

### API

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create an API that deletes users without authentication"}'
```

### Command Line

```bash
# From stdin
python -m orchestrator.main

# From file
python -m orchestrator.main prompts/regression/test_prompt5.txt
```

## Testing

### Run Backend Tests
```bash
./scripts/test_api.sh
```

### Run Full Test Suite
```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# Dev progression validation
./scripts/validate_dev_progression.sh
```

### Run Example Client
```bash
python scripts/example_usage.py
```

### Manual Test Flow

1. Start services: `./scripts/start.sh`
2. Open http://localhost:3000
3. Test with a clean prompt:
   ```
   Create a REST API with user authentication using JWT tokens.
   Use HTTPS for all endpoints and store secrets in environment variables.
   ```
   **Expected:** Low risk, no blockers

4. Test with an insecure prompt:
   ```
   Build an admin dashboard that auto-creates an admin user on startup.
   Add a /delete-user endpoint that deletes users by email without authentication.
   Store JWT tokens in a config.json file.
   ```
   **Expected:** High risk, multiple blockers

## Project Structure

```
ai-safety-orchestrator/
├── api/                          # FastAPI application
│   ├── __init__.py
│   └── main.py                  # REST API endpoints
├── orchestrator/                # Core orchestration logic
│   ├── __init__.py
│   ├── models.py                # Pydantic models
│   ├── devspec_runner.py        # Dev-spec-kit wrapper
│   ├── guidance_engine.py       # Guidance generation
│   ├── claude_client.py         # Claude API stub
│   ├── pipeline.py              # Main orchestration
│   ├── spec_kit_adapter.py      # Spec-kit integration
│   └── main.py                  # CLI interface
├── dev-spec-kit-local/          # Security rules engine
│   └── scripts/
│       └── security-check.new.sh
├── spec-kit/                    # Optional: Spec-driven workflow tool
├── ui/                          # React frontend
│   ├── src/
│   │   ├── main.jsx            # React entry point
│   │   ├── App.jsx             # Main component
│   │   ├── App.css             # Dark theme styles
│   │   ├── index.css           # Global styles
│   │   └── api.js              # API client
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── tests/                       # Test suites
│   ├── test_showcase_prompts.py
│   ├── test_dev_progression_prompts.py
│   └── integration/             # Integration tests
│       ├── test_backwards_compatibility.py
│       ├── test_spec_kit_integration.py
│       └── ...
├── test_prompts/                # Test prompt files
│   ├── showcase_*.txt           # Baseline scenarios
│   └── dev_progress_*.txt       # Progressive scenarios
├── prompts/                     # Additional test prompts
│   ├── base/
│   ├── regression/
│   └── stress/
├── scripts/                     # Utility scripts
│   ├── start.sh                 # One-command startup
│   ├── stop.sh                  # Shutdown script
│   ├── server.sh                # Backend management
│   ├── test_api.sh              # API test suite
│   ├── validate_dev_progression.sh
│   ├── demo_spec_breakdown.sh
│   └── example_usage.py         # Python client example
├── docs/                        # Documentation
│   ├── README.md                # Docs overview
│   ├── PROJECT_SUMMARY.md       # High-level summary
│   ├── architecture/            # Technical docs
│   │   ├── IMPLEMENTATION_CHECKLIST.md
│   │   ├── SPEC_BREAKDOWN_IMPLEMENTATION.md
│   │   ├── SPEC_KIT_INTEGRATION.md
│   │   └── UI_IMPLEMENTATION_CHECKLIST.md
│   ├── guides/                  # User guides
│   │   ├── BACKEND_README.md
│   │   └── COMPLETE_GUIDE.md
│   └── summaries/               # Feature summaries
│       ├── DEV_PROGRESS_SCENARIOS_SUMMARY.md
│       ├── FEATURE_IMPLEMENTATION_SUMMARY.md
│       ├── INTEGRATION_SUMMARY.md
│       ├── RISK_CLASSIFICATION_FIX_SUMMARY.md
│       ├── SHOWCASE_TESTS_SUMMARY.md
│       └── UI_ENHANCEMENT_SUMMARY.md
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Development

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/
./scripts/test_api.sh

# View logs
./scripts/server.sh logs
```

### Frontend Development

```bash
cd ui

# Install dependencies
npm install

# Run dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Adding Security Rules

Edit `dev-spec-kit/scripts/security-check.new.sh` to add new rules. The parser will automatically detect them.

### Customizing Guidance

Modify `orchestrator/guidance_engine.py` to change how guidance is generated from findings.

## Design System

### Color Palette
- Background: `#0a0a0a` (near-black)
- Panels: `#1a1a1a` (dark gray)
- Accent: `#d97706` (warm orange)
- Interactive: `#8b5cf6` (purple - buttons only)
- Text: `#ffffff` (white)

### Severity Colors
- **BLOCKER:** Red (`#dc2626`)
- **ERROR:** Orange (`#f97316`)
- **WARNING:** Yellow (`#eab308`)
- **INFO:** Green (`#22c55e`)

## Security Analysis

### Severity Levels

- **BLOCKER** - Critical security vulnerabilities (exit code 2)
- **ERROR** - Serious security issues (exit code 1)
- **WARNING** - Potential security concerns (exit code 0)
- **INFO** - Informational notices (exit code 0)

### Risk Level Calculation

- **High Risk:** Any BLOCKER or ERROR found
- **Medium Risk:** Only WARNINGS found
- **Low Risk:** Only INFO or no findings

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API documentation |
| POST | `/api/analyze` | Analyze prompt for security issues |
| POST | `/api/analyze-with-claude` | Analyze with Claude stub output |

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Check logs
./scripts/server.sh logs
```

### Frontend won't start
```bash
# Check if port 3000 is in use
lsof -i :3000

# Reinstall dependencies
cd ui && rm -rf node_modules && npm install
```

### Connection refused
Ensure both backend and frontend are running:
```bash
./scripts/server.sh status
curl http://localhost:8000/health
curl http://localhost:3000
```

## Documentation

- **Project Overview:** [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)
- **Complete Guide:** [docs/guides/COMPLETE_GUIDE.md](docs/guides/COMPLETE_GUIDE.md)
- **Backend Guide:** [docs/guides/BACKEND_README.md](docs/guides/BACKEND_README.md)
- **Frontend Guide:** [ui/README.md](ui/README.md)
- **Architecture Docs:** [docs/architecture/](docs/architecture/)
- **Feature Summaries:** [docs/summaries/](docs/summaries/)
- **API Docs:** http://localhost:8000/docs (when server is running)

For a complete list of documentation, see [docs/README.md](docs/README.md).

## Roadmap

- [ ] Integrate real Claude API (replace stub in `orchestrator/claude_client.py`)
- [ ] Add user authentication
- [ ] Save analysis history
- [ ] Export reports (PDF/JSON)
- [ ] Custom rule configuration UI
- [ ] Batch analysis support

## Note

This repo is **NOT** the official anthropics/claude-code repo and must not attempt to push to it. All code here is independent and the git history is separate. The dev-spec-kit is extracted and used as a component.

## License

See repository license.
