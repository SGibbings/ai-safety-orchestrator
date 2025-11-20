# Preflight Prompt Security & Quality Rule Engine

This directory contains the enhanced `security-check.sh` and related logic for preflight validation of developer prompts before they are sent to an AI code model.

## Categories & Severity Levels

- **Categories:**
  - SECURITY: Risks to confidentiality, integrity, or availability
  - ARCH: Architecture/design issues
  - AMBIG: Ambiguity or under-specification
  - QUALITY: Quality, governance, or best-practice gaps

- **Severity:**
  - INFO: Minor suggestion, low risk
  - WARNING: Real concern, not a blocker
  - ERROR: Serious concern, should not proceed as-is
  - BLOCKER: Must fix before proceeding

## How to Add/Modify Rules

1. Edit `security-check.sh` and locate the RULES section.
2. Each rule is a function with:
   - Category, Severity, Code/ID, Message, (optional) Suggestion
3. Add new rules by following the pattern.
4. To adjust severity or message, edit the rule function or its regex/logic.

## Example Usage

```bash
bash claude-code/plugins/dev-spec-kit/scripts/security-check.sh test_prompt.txt
```

## Example Output

Total warnings: 7 (INFO: 1, WARNING: 3, ERROR: 2, BLOCKER: 1)

[SECURITY][ERROR][SEC_UNAUTH_DELETE]
Detected an endpoint that deletes users by email without authentication.
Suggestion: Require authenticated admin role and proper access control before deletion.

[ARCH][WARNING][ARCH_CONFLICTING_TECH]
Prompt requests both Express (Node.js) and FastAPI (Python) in a single microservice.
Suggestion: Choose a single backend framework and language for this service.

...etc...

## Test Prompts

See `test_prompt.txt` for a complex example that should trigger many warnings.

---

**Maintainers:**
- To update rules, edit `security-check.sh` and follow the function-based rule pattern.
- To add new test prompts, add files in this directory and run the script to check output.
