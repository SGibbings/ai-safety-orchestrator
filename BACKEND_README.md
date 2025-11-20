# SpecAlign - Backend API

A FastAPI-based backend that orchestrates security analysis for AI-assisted development prompts.

## Architecture

The backend consists of three main components:

1. **Dev Spec Kit Integration** - Wraps the shell-based security rules engine
2. **Guidance Engine** - Adds additional security constraints and curated prompts
3. **Claude Client** - Placeholder for future Claude API integration

## Project Structure

```
ai-safety-orchestrator/
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI application
├── orchestrator/
│   ├── __init__.py
│   ├── models.py            # Pydantic models
│   ├── devspec_runner.py    # Dev-spec-kit wrapper
│   ├── guidance_engine.py   # Guidance generation
│   ├── claude_client.py     # Claude API stub
│   ├── pipeline.py          # Main orchestration logic
│   └── main.py              # CLI interface
├── dev-spec-kit/
│   └── scripts/
│       └── security-check.new.sh
├── requirements.txt
└── test_api.sh
```

## Installation

1. Ensure you're in the repository root:
```bash
cd /workspaces/ai-safety-orchestrator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the API Server

Start the FastAPI server:

```bash
python api/main.py
```

Or use uvicorn directly with hot-reload:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Interactive docs (Swagger UI): `http://localhost:8000/docs`
- Alternative docs (ReDoc): `http://localhost:8000/redoc`

### API Endpoints

#### `GET /`
Returns API information and status.

#### `GET /health`
Health check endpoint.

#### `POST /api/analyze`
Analyze a developer prompt for security issues.

**Request Body:**
```json
{
  "prompt": "Your developer prompt here"
}
```

**Response:**
```json
{
  "original_prompt": "...",
  "normalized_prompt": "...",
  "devspec_raw_output": "...",
  "devspec_findings": [
    {
      "category": "SECURITY",
      "severity": "BLOCKER",
      "code": "SEC_UNAUTH_DELETE",
      "message": "...",
      "suggestion": "..."
    }
  ],
  "guidance": [
    {
      "title": "...",
      "detail": "..."
    }
  ],
  "final_curated_prompt": "...",
  "claude_output": null,
  "exit_code": 2,
  "has_blockers": true,
  "has_errors": false
}
```

#### `POST /api/analyze-with-claude`
Same as `/api/analyze` but includes Claude stub output in the `claude_output` field.

### Command-Line Interface

You can also use the CLI to analyze prompts:

```bash
# From stdin
python -m orchestrator.main

# From file
python -m orchestrator.main test_prompt5.txt
```

### Testing

Run the test suite:

```bash
./test_api.sh
```

Or test individual prompts:

```bash
# Test via CLI
python -m orchestrator.main test_prompt5.txt

# Test via API (requires server to be running)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "prompt": "Create a photo sharing app where users can download images without authentication."
}
EOF
```

## Security Analysis Flow

1. **Input**: Raw developer prompt
2. **Dev-Spec-Kit**: Shell script analyzes prompt for security patterns
3. **Parsing**: Output is parsed into structured findings
4. **Guidance**: Additional constraints are generated based on findings
5. **Curation**: Original prompt is enhanced with security requirements
6. **Output**: Complete analysis with findings, guidance, and curated prompt

## Exit Codes

The dev-spec-kit script returns:
- `0` - No errors or blockers (warnings only)
- `1` - Errors found
- `2` - Blockers found (critical security issues)

## Severity Levels

- **BLOCKER** - Critical security vulnerabilities that must be fixed
- **ERROR** - Serious security issues that should be addressed
- **WARNING** - Potential security concerns to consider
- **INFO** - Informational notices

## Extending the System

### Adding New Security Rules

Add rules to `dev-spec-kit/scripts/security-check.new.sh`. The parser will automatically detect them.

### Customizing Guidance

Modify `orchestrator/guidance_engine.py` to change how guidance is generated from findings.

### Integrating Claude API

Replace the stub in `orchestrator/claude_client.py` with actual API calls:

```python
import anthropic

def call_claude(final_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": final_prompt}]
    )
    return message.content[0].text
```

## Development

### Adding Dependencies

Add to `requirements.txt` and reinstall:

```bash
echo "new-package" >> requirements.txt
pip install -r requirements.txt
```

### Code Structure

- **Models** (`models.py`): All Pydantic models for validation
- **Runner** (`devspec_runner.py`): Subprocess wrapper for shell scripts
- **Guidance** (`guidance_engine.py`): Business logic for constraint generation
- **Pipeline** (`pipeline.py`): Orchestrates the complete flow
- **API** (`api/main.py`): FastAPI routes and endpoints

## Troubleshooting

### Server won't start
- Check if port 8000 is available: `lsof -i :8000`
- Check logs: `tail -f /tmp/api.log`

### Dev-spec-kit not found
- Verify the script exists: `ls -la dev-spec-kit/scripts/`
- Check file permissions: `chmod +x dev-spec-kit/scripts/security-check.new.sh`

### Import errors
- Ensure you're running from repo root
- Verify Python path: `echo $PYTHONPATH`
- Reinstall dependencies: `pip install -r requirements.txt`

## License

See repository license.
