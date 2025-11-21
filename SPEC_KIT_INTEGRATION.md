# Spec-Kit Integration Guide

## Overview

SpecAlign now supports optional integration with GitHub's [spec-kit](https://github.com/github/spec-kit) as an **additive layer** that runs before the existing dev-spec-kit security analysis.

**Critical: spec-kit is ADDITIVE, not a replacement**
- spec-kit is a spec-driven development workflow tool
- dev-spec-kit is your security analysis engine
- When enabled, spec-kit runs first, then dev-spec-kit **always** runs after
- spec-kit **cannot** bypass or replace security checks

## Architecture

```
User Prompt
    ↓
[Optional] spec-kit workflow analysis ← USE_SPEC_KIT=true
    ↓
dev-spec-kit security analysis ← ALWAYS runs
    ↓
filter_false_positives
    ↓
risk_level computation
    ↓
AnalysisResponse (with optional spec-kit fields)
```

## Usage

### Default Behavior (spec-kit disabled)

By default, spec-kit is **disabled** and the pipeline works exactly as before:

```bash
# No environment variable needed - spec-kit is off by default
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a secure API with OAuth2"}'
```

Response includes security analysis only:
```json
{
  "risk_level": "Low",
  "devspec_findings": [],
  "spec_kit_enabled": false,
  "spec_kit_success": null,
  "spec_kit_raw_output": null,
  "spec_kit_summary": null
}
```

### Enabling spec-kit

Set the `USE_SPEC_KIT` environment variable:

```bash
# Enable spec-kit
export USE_SPEC_KIT=true

# Start the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Response now includes both spec-kit and security analysis:
```json
{
  "risk_level": "Low",
  "devspec_findings": [],
  "spec_kit_enabled": true,
  "spec_kit_success": true,
  "spec_kit_raw_output": "...",
  "spec_kit_summary": "spec-kit completed (workflow tool, not security analyzer)"
}
```

## API Response Fields

### Existing Fields (unchanged)
- `original_prompt`: The input prompt
- `normalized_prompt`: Cleaned prompt text
- `devspec_raw_output`: Raw output from dev-spec-kit
- `devspec_findings`: List of security findings
- `guidance`: Additional guidance items
- `final_curated_prompt`: Refined prompt with security constraints
- `claude_output`: Claude API output (if enabled)
- `exit_code`: Exit code from dev-spec-kit
- `has_blockers`: Whether BLOCKER issues were found
- `has_errors`: Whether ERROR issues were found
- `risk_level`: Overall risk level (Low/Medium/High)

### New spec-kit Fields (backwards compatible)
- `spec_kit_enabled` (bool): Whether spec-kit was used
  - `false` by default
- `spec_kit_success` (bool | null): Whether spec-kit call succeeded
  - `null` when disabled
  - `true` when successful
  - `false` when failed
- `spec_kit_raw_output` (string | null): Raw output from spec-kit
  - `null` when disabled or failed
- `spec_kit_summary` (string | null): Summary of spec-kit results
  - `null` when disabled

## Guarantees

### 1. Backwards Compatibility
Existing clients work without changes:
- spec-kit fields default to `false`/`null`
- Security analysis behavior is **identical**
- No breaking changes to existing fields

### 2. Security Analysis Always Runs
dev-spec-kit security analysis **always** executes, even when:
- spec-kit is enabled
- spec-kit fails or times out
- spec-kit returns errors

### 3. Consistent Risk Assessment
`risk_level`, `has_blockers`, and `has_errors` are **identical** regardless of spec-kit status:
- With `USE_SPEC_KIT=false`: Based on dev-spec-kit findings
- With `USE_SPEC_KIT=true`: Based on dev-spec-kit findings (spec-kit is informational)

### 4. Failure Handling
If spec-kit fails:
- Error is logged
- `spec_kit_success` is set to `false`
- Pipeline continues to dev-spec-kit
- Security analysis completes normally

## Code Structure

### Adapter Layer
All spec-kit access goes through `orchestrator/spec_kit_adapter.py`:
```python
from orchestrator.spec_kit_adapter import should_use_spec_kit, get_adapter

if should_use_spec_kit():
    adapter = get_adapter()
    spec_result = adapter.analyze_prompt(prompt)
```

### Isolation
Direct spec-kit references are **only** allowed in:
- `spec-kit/` (the submodule itself)
- `orchestrator/spec_kit_adapter.py` (adapter layer)
- `orchestrator/pipeline.py` (main pipeline)
- `orchestrator/models.py` (response models)
- Test files
- Documentation

All other code must use the adapter.

### Guardrails
Run `test_spec_kit_references.py` to verify no unauthorized coupling:
```bash
python3 test_spec_kit_references.py
```

## Testing

### Test Suites
```bash
# Test spec-kit integration (adapter layer)
python3 test_spec_kit_integration.py

# Test additive behavior (spec-kit + dev-spec-kit)
python3 test_spec_kit_additive.py

# Test security analysis (original behavior)
python3 test_risk_classification.py

# Test isolation (guardrails)
python3 test_spec_kit_references.py

# Run all tests
python3 test_spec_kit_references.py && \
  python3 test_spec_kit_integration.py && \
  python3 test_spec_kit_additive.py && \
  python3 test_risk_classification.py
```

### Key Test Scenarios
1. **Default mode** (spec-kit off): Behavior identical to pre-integration
2. **Spec-kit mode** (spec-kit on): Both spec-kit and dev-spec-kit run
3. **Consistency**: Security analysis identical in both modes
4. **Failure handling**: dev-spec-kit runs even if spec-kit fails
5. **Backwards compatibility**: Existing clients work unchanged

## Important Notes

### What spec-kit IS
- A spec-driven development workflow tool
- Helps with project scaffolding and planning
- NOT a security analyzer

### What spec-kit is NOT
- NOT a replacement for dev-spec-kit
- NOT a security scanning tool
- NOT required for security analysis

### Integration Purpose
This integration exists to:
- Optionally augment workflows with spec-kit tooling
- Maintain strict separation from security analysis
- Provide additive functionality without breaking existing behavior

## Troubleshooting

### spec-kit fields are null/false
This is **expected** when `USE_SPEC_KIT` is not set. The pipeline works normally.

### spec-kit fails but pipeline continues
This is **correct behavior**. Security analysis always completes.

### Security findings differ between modes
This is a **bug**. Security findings must be identical. File an issue.

### Want to disable spec-kit
Simply unset or set to false:
```bash
unset USE_SPEC_KIT
# or
export USE_SPEC_KIT=false
```

## Development

### Adding spec-kit References
If you need to reference spec-kit:
1. Use `orchestrator/spec_kit_adapter.py` (preferred)
2. If adding to new files, update `test_spec_kit_references.py` ALLOWED_PATHS
3. Run guardrail test to verify isolation

### Modifying Integration
Changes must:
1. Keep dev-spec-kit as primary security analyzer
2. Maintain backwards compatibility (spec-kit off by default)
3. Pass all test suites
4. Keep spec-kit additive (never replace security analysis)

## References

- spec-kit repository: https://github.com/github/spec-kit
- dev-spec-kit: `dev-spec-kit-local/` (existing security engine)
- Adapter: `orchestrator/spec_kit_adapter.py`
- Pipeline: `orchestrator/pipeline.py`
- Tests: `test_spec_kit_*.py`
