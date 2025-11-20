# AI Safety Orchestrator

This is a standalone project that uses the Dev Spec Kit (extracted from claude-code) as a component.

## High-level flow
- Developer prompt → Orchestrator → Dev Spec Kit checks + custom guidance layer → Final curated prompt → Claude → result.

## Architecture
- `dev-spec-kit/` — Security and quality check engine (copied from claude-code)
- `orchestrator/` — Custom logic layer (accepts prompt, calls Dev Spec Kit, applies guidance)
- `ui/` — Frontend (user enters prompt, sees results)

**Note:**
- This repo is NOT the official anthropics/claude-code repo and must not attempt to push to it.
- All code here is independent and the git history is separate.
