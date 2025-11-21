# Prompts Directory

This directory contains all prompt files used for testing, demos, and regression validation.

## Directory Structure

```
prompts/
├── base/          # Simple, clean example prompts
│   ├── test_prompt_clean.txt      # Clean secure API example
│   ├── test_prompt_clean2.txt     # Another clean example
│   └── test_safe_prompt.txt       # Safe prompt for testing
│
├── stress/        # High-risk and edge case prompts
│   ├── high1.txt                  # High-risk scenario 1
│   ├── high2.txt                  # High-risk scenario 2 (intentionally insecure)
│   ├── medium1.txt                # Medium-risk scenario 1
│   ├── medium2.txt                # Medium-risk scenario 2
│   ├── low1.txt                   # Low-risk scenario 1
│   ├── low2.txt                   # Low-risk scenario 2
│   ├── test_prompt_stress.txt     # Stress test prompt
│   ├── test_prompt_blocked2.txt   # Should be blocked
│   └── test_prompt_medium.txt     # Medium complexity
│
├── regression/    # Prompts for regression testing
│   ├── test_prompt.txt            # Original test case
│   ├── test_prompt4.txt through test_prompt11.txt
│   └── test_prompt_medium.txt     # Medium complexity test
│
└── demo/          # Demo and example prompts
    └── test_case.txt              # Simple demo case
```

## File Naming Conventions

- **base/** - Use descriptive names like `clean_api.txt`, `secure_auth.txt`
- **stress/** - Use severity levels: `high*.txt`, `medium*.txt`, `low*.txt`
- **regression/** - Use sequential numbering: `test_prompt*.txt`
- **demo/** - Use descriptive names for demonstrations

## Usage

### In Tests

```python
# Python tests
with open('prompts/stress/high2.txt') as f:
    prompt = f.read()
```

```bash
# Shell scripts
PROMPT=$(cat prompts/regression/test_prompt5.txt)
```

### In Documentation

When referencing prompts in docs, use full paths from repo root:
- `prompts/stress/high2.txt`
- `prompts/base/test_prompt_clean.txt`

### Adding New Prompts

1. Choose the appropriate subdirectory based on purpose:
   - **base/** - Clean, simple examples showing best practices
   - **stress/** - Security edge cases, intentionally problematic code
   - **regression/** - Prompts that have triggered bugs or need ongoing validation
   - **demo/** - User-facing examples for tutorials/demos

2. Use descriptive filenames that indicate the prompt's purpose

3. Add a comment at the top of the file explaining what it tests (if not obvious)

4. Update this README if adding a new category

## Maintenance

- Keep prompts focused on one concept/issue when possible
- Remove duplicate or obsolete prompts
- Update references in scripts/tests when moving files
- Document any prompts used in CI/CD pipelines

## Related Files

- Test scripts: `test_api.sh`, `test_full_stack.sh`, `demo_spec_breakdown.sh`
- Python tests: `test_*.py` files in repo root
- Documentation: References in `README.md`, `COMPLETE_GUIDE.md`, etc.
