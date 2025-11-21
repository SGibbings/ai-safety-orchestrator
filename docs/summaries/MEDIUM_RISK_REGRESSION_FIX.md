# Medium Risk Regression Fix - Summary

## Problem

The system was producing only High or Low risk levels. Medium risk became unreachable even though:
- Score ranges were correct
- Security findings were correct  
- Regression tests were still green

This indicated the risk classification layer had regressed.

## Root Cause

Missing security rules for certain ERROR-level scenarios:
1. **Debug endpoints with 10-49 records** - Only had rules for 50+ (ERROR) and 100+ (BLOCKER), but 10-49 fell through to WARNING
2. **Trusting gateway headers** - No rule existed for this common security boundary violation

## Solution

### 1. Added Missing Security Rules

**File**: `dev-spec-kit-local/scripts/security-check.new.sh`

#### SEC_DEBUG_EXPOSES_MULTIPLE_IDS (ERROR)
Detects debug endpoints exposing 10-49 user IDs/records:
```bash
# Pattern: /debug/activity returns last 10 user IDs
# Severity: ERROR (privacy risk even with small batches)
```

#### SEC_TRUSTS_GATEWAY_HEADER (ERROR)  
Detects trusting x-user-id or similar headers from gateway/proxy:
```bash
# Pattern: Service trusts the x-user-id header passed in by gateway
# Severity: ERROR (enables impersonation without validation)
```

### 2. Risk Classification Logic (Already Correct)

The pipeline logic in `orchestrator/pipeline.py` was already correct:

```python
if has_blockers:
    risk_level = "High"
elif has_errors:
    risk_level = "Medium"  # ← This path was unreachable due to missing rules
elif has_warnings:
    risk_level = "Low"
else:
    risk_level = "Low"
```

The issue was that prompts that should have produced ERROR findings were falling through to WARNING or no findings.

### 3. New Regression Test Suite

**File**: `tests/test_medium_risk_regression.py`

**10 comprehensive tests** to prevent future regressions:
- 4 parametrized Medium risk tests (PII logging, weak hash, debug endpoint, header trust)
- 2 control tests (Low and High risk)
- 4 invariant tests (classification logic, BLOCKER exclusion, ERROR requirement, ordering)

## Validation

### Test Prompts (All Pass)

| Prompt | Description | Expected Risk | Actual Risk | Finding |
|--------|-------------|---------------|-------------|---------|
| **A** | PII logging | Medium | ✅ Medium | SEC_LOGS_PII_EMAIL |
| **B** | Weak hash (SHA-256) | Medium | ✅ Medium | SEC_WEAK_PASSWORD_HASH_SHA256 |
| **C** | Debug endpoint (10 IDs) | Medium | ✅ Medium | SEC_DEBUG_EXPOSES_MULTIPLE_IDS |
| **D** | Minimal spec | Low | ✅ Low | None |
| **E** | Trusts gateway header | Medium | ✅ Medium | SEC_TRUSTS_GATEWAY_HEADER |
| **F** | Logs raw passwords | High | ✅ High | SEC_LOGS_PASSWORDS |

### Test Results

```
tests/test_showcase_prompts.py           11 passed ✅
tests/test_dev_progression_prompts.py    14 passed ✅
tests/test_medium_risk_regression.py     10 passed ✅
────────────────────────────────────────────────────
Total:                                   35 passed ✅
```

**No existing tests were modified or broken.**

## Files Changed

### Security Rules
- `dev-spec-kit-local/scripts/security-check.new.sh`
  - Added `SEC_DEBUG_EXPOSES_MULTIPLE_IDS` (ERROR)
  - Added `SEC_TRUSTS_GATEWAY_HEADER` (ERROR)

### Test Files
- `tests/test_medium_risk_regression.py` (new)
- `test_prompts/medium_test_a_pii.txt` (new)
- `test_prompts/medium_test_b_hash.txt` (new)
- `test_prompts/medium_test_c_debug.txt` (new)
- `test_prompts/medium_test_d_low.txt` (new)
- `test_prompts/medium_test_e_header.txt` (new)
- `test_prompts/medium_test_f_high.txt` (new)

## Risk Classification Matrix

| Severity Present | Risk Level | Exit Code |
|-----------------|------------|-----------|
| BLOCKER | **High** | 2 |
| ERROR (no BLOCKER) | **Medium** | 1 |
| WARNING (no ERROR/BLOCKER) | **Low** | 0 |
| None | **Low** | 0 |

## Acceptance Criteria ✅

All criteria met:

- ✅ Prompts A, B, C, E → Medium risk
- ✅ Prompt D → Low risk  
- ✅ Prompt F → High risk
- ✅ All 25 existing tests pass unchanged
- ✅ New regression test suite validates Medium risk is reachable

## Conclusion

Medium risk is now correctly assigned when ERROR-level findings exist without BLOCKER-level findings. The fix adds two missing security rules without modifying any existing logic or tests. All 35 tests pass (25 existing + 10 new).
