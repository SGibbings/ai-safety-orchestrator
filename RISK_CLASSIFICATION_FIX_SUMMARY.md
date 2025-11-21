# Risk Classification Fix Summary

## Problem Statement

The SpecAlign risk classification system was marking **all prompts as High Risk**, even secure, well-specified prompts with good security hygiene. This was due to:

1. **Overly aggressive false-positive triggers** - Security rules triggering on mentions of security concepts (e.g., "use environment variables for secrets" triggered "SEC_HARDCODED_SECRET")
2. **Too strict risk thresholds** - Any ERROR or BLOCKER → High Risk (no Medium tier)
3. **Missing severity gradation** - Debug endpoints exposing IDs treated same as those exposing secrets

## Changes Implemented

### 1. False-Positive Filtering (dev-spec-kit-local/scripts/security-check.new.sh)

#### SEC_HARDCODED_SECRET - Fixed
**Before:** Triggered on any mention of "secret", "key", "password"
**After:** Only triggers if NOT using environment variables or secret management
```bash
# Now checks for negation patterns
&& ! grep -iqE 'environment variable|env var|secret manager|from env|getenv|process\.env|os\.environ'
```

**Impact:** Prompt A no longer false-triggers when explicitly using env vars

#### SEC_DEBUG_EXPOSES_SECRETS - Refined
**Before:** Triggered on `/debug.*secret` (even if "secret" mentioned elsewhere in prompt)
**After:** Only triggers when debug endpoint directly returns secrets
```bash
# More specific pattern matching
'/debug[^ ]*\s+(return|returns)\s+(all |the |last [0-9]+ )?(token|session|credential|password|secret)'
```

**Impact:** Prompt B no longer triggers when saying "no raw tokens"

#### SEC_DEBUG_EXPOSES_PII - New Rule (ERROR)
**Added:** Separate rule for PII (emails) exposure - ERROR severity, not BLOCKER
```bash
elif grep -iqE '/debug.*(return|returns|show|shows|expose|exposes)\s+(all |the |last [0-9]+ )?email'
```

**Impact:** Prompt B correctly identified as Medium (ERROR) not High (BLOCKER)

#### SEC_DEBUG_EXPOSES_METADATA - New Rule (WARNING)
**Added:** Non-sensitive metadata (IDs, filenames) - WARNING severity only
```bash
elif grep -iqE '/debug.*(return|returns)\s+(all |the |last [0-9]+ )?(user|id|filename)'
  add_warning "SECURITY" "WARNING" "SEC_DEBUG_EXPOSES_METADATA"
```

**Impact:** Debug endpoints showing only IDs → WARNING, not blocking deployment

#### SEC_NO_TLS_FOR_AUTH - Fixed
**Before:** Triggered if auth mentioned without explicit "https" in prompt
**After:** Only triggers if HTTP explicitly used AND no reverse proxy mentioned
```bash
if grep -iqE 'http://' && ... && ! grep -iqE 'https|tls|behind.*nginx|nginx.*handle.*tls'
```

**Impact:** Prompt B with "Let Nginx handle HTTPS" no longer false-triggers

#### SEC_MISSING_INPUT_VALIDATION - Fixed
**Before:** Triggered on "assume.*frontend.*validat" (too broad)
**After:** Only triggers on explicit skip statements
```bash
if grep -iqE 'skip (input )?validation|no (input )?validation|assume (input )?safe|trust (client|frontend) input'
```

**Impact:** Prompts not explicitly skipping validation no longer trigger

#### SEC_WEAK_PASSWORD_HASH_SHA256 - New Rule (ERROR)
**Added:** SHA-256 for passwords detected as ERROR (not BLOCKER)
```bash
if grep -iqE '(password|hash).*(using|with|use).*(sha-?256)'
  || (grep -iqE 'sha-?256' && grep -iqE 'password.*hash' && ! grep -iqE 'not.*sha-?256|instead of.*sha-?256')
```

**Impact:** Prompt C detects SHA-256 as ERROR (moderate concern, not catastrophic)

#### SEC_ADMIN_BACKDOOR - Enhanced
**Before:** Only caught "admin.*(auto-create|regenerat)"
**After:** Also catches hardcoded/default admin users
```bash
if grep -iqE 'admin.*(hardcoded|hard-coded|default|built-in)|(hardcoded|default).*(admin.*user|admin.*account)'
```

**Impact:** Prompt C detects "Hardcoded default admin user in config"

---

### 2. Risk Classification Logic (orchestrator/pipeline.py)

#### Before:
```python
if has_blockers or has_errors:
    risk_level = "High"
elif has_warnings:
    risk_level = "Medium"
else:
    risk_level = "Low"
```

#### After:
```python
if has_blockers:
    risk_level = "High"       # Critical issues only
elif has_errors:
    risk_level = "Medium"     # Significant but not catastrophic
elif has_warnings:
    risk_level = "Low"        # Minor concerns, still flag
else:
    risk_level = "Low"        # Clean
```

**Impact:**
- Prompts with only ERRORs → Medium (not High)
- Prompts with only WARNINGs → Low (not Medium)
- Clear severity hierarchy: BLOCKER → High, ERROR → Medium, WARNING → Low

---

## Test Results

### Prompt A: Secure Service ✅

**Description:** Well-specified FastAPI service with HTTPS, OAuth2, bcrypt, env vars, no logging of secrets

**Before Fix:**
- Risk: High (❌ False positive)
- Score: 84
- Issues: 2 (SEC_HARDCODED_SECRET, SEC_MISSING_INPUT_VALIDATION)

**After Fix:**
- Risk: Low (✅ Correct)
- Score: 84
- Issues: 0

**Verdict:** PASS ✓ - Secure prompts correctly identified

---

### Prompt B: Medium Risk Service ✅

**Description:** Internal Node.js service with bcrypt, env vars, but debug endpoint exposing emails/IDs

**Before Fix:**
- Risk: High (❌ Too strict)
- Score: 29
- Issues: 2 BLOCKERS (SEC_HARDCODED_SECRET, SEC_DEBUG_EXPOSES_SECRETS)

**After Fix:**
- Risk: Medium (✅ Correct)
- Score: 29
- Issues: 1 ERROR (SEC_DEBUG_EXPOSES_PII)

**Verdict:** PASS ✓ - Moderate risks correctly identified

---

### Prompt C: Dangerous Service ✅

**Description:** Go service with HTTP only, SHA-256 passwords, hardcoded admin, hardcoded JWT secret, debug endpoint

**Before Fix:**
- Risk: High (✅ Correct, but missing some issues)
- Score: 23
- Issues: 3 BLOCKERS (missing SHA-256, missing admin backdoor)

**After Fix:**
- Risk: High (✅ Correct)
- Score: 23
- Issues: 4 BLOCKERS + 1 ERROR
  - SEC_ADMIN_BACKDOOR (BLOCKER)
  - SEC_INSECURE_JWT_STORAGE (BLOCKER)
  - SEC_HARDCODED_SECRET (BLOCKER)
  - SEC_HTTP_FOR_AUTH (BLOCKER)
  - SEC_WEAK_PASSWORD_HASH_SHA256 (ERROR)

**Verdict:** PASS ✓ - Dangerous prompts correctly identified with all issues caught

---

## Regression Tests Created

**File:** `tests/test_risk_profiles.py`

**Test Coverage:**
1. `test_prompt_a_secure_service_low_risk()` - Verifies secure prompt → Low
2. `test_prompt_b_medium_risk_service()` - Verifies moderate prompt → Medium
3. `test_prompt_c_dangerous_service_high_risk()` - Verifies dangerous prompt → High
4. `test_risk_level_distribution()` - Verifies A/B/C produce different risk levels
5. `test_spec_quality_score_correlation()` - Verifies scores correlate with completeness

**Results:** ✅ ALL 5 TESTS PASSING

**Run Command:**
```bash
USE_SPEC_KIT=true python tests/test_risk_profiles.py
```

---

## Summary Statistics

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| **Prompt A Risk** | High ❌ | Low ✅ | Fixed |
| **Prompt B Risk** | High ❌ | Medium ✅ | Fixed |
| **Prompt C Risk** | High ✅ | High ✅ | Maintained |
| **False Positives** | 4 | 0 | Eliminated |
| **Risk Tiers Used** | 2 (High/Low) | 3 (High/Medium/Low) | Improved |
| **Severity Detection** | Missing 2 issues | All issues caught | Improved |
| **Test Coverage** | None | 5 tests | Added |

---

## Key Improvements

### 1. Precision Over Recall
- **Before:** Cast wide net, caught everything as High Risk
- **After:** Precise targeting of actual issues, proper severity gradation

### 2. Context-Aware Detection
- **Before:** Keyword matching (mention "secret" → trigger)
- **After:** Pattern analysis (using secrets properly vs. hardcoding)

### 3. Severity Hierarchy
- **BLOCKER:** Critical vulnerabilities requiring immediate fix (High Risk)
- **ERROR:** Significant security issues that should be addressed (Medium Risk)
- **WARNING:** Best practices, minor concerns (Low Risk)

### 4. PII Sensitivity
- **New distinction:** Secrets (BLOCKER) vs. PII (ERROR) vs. Metadata (WARNING)
- **Impact:** More nuanced privacy handling

---

## Files Modified

1. **dev-spec-kit-local/scripts/security-check.new.sh** (copied to security-check.sh)
   - 8 rule improvements
   - 3 new rules added
   - Better false-positive filtering

2. **orchestrator/pipeline.py**
   - Risk classification logic updated
   - Clear severity hierarchy

3. **tests/test_risk_profiles.py** (NEW)
   - 5 comprehensive tests
   - Prevents regression

4. **test_prompts/prompt_a_secure.txt** (NEW)
5. **test_prompts/prompt_b_medium.txt** (NEW)
6. **test_prompts/prompt_c_dangerous.txt** (NEW)

---

## Verification

### Manual Testing
```bash
# Test all three prompts
USE_SPEC_KIT=true curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "..."}'
```

### Automated Testing
```bash
# Run regression suite
USE_SPEC_KIT=true python tests/test_risk_profiles.py
```

### Expected Output
```
✅ ALL TESTS PASSED

Risk classification is working correctly:
- Secure prompts → Low Risk
- Moderate prompts → Medium Risk
- Dangerous prompts → High Risk
```

---

## Impact on Users

### Before
- ❌ Users frustrated by all prompts marked High Risk
- ❌ No differentiation between secure and dangerous
- ❌ False positives erode trust in system
- ❌ Users might ignore warnings ("crying wolf")

### After
- ✅ Accurate risk assessment builds trust
- ✅ Clear differentiation helps prioritization
- ✅ Medium tier enables incremental improvement
- ✅ Warnings are meaningful and actionable

---

## Future Considerations

### Potential Enhancements
1. **Configurable Thresholds:** Allow users to adjust severity mappings
2. **Context Learning:** Track false-positive patterns over time
3. **Domain-Specific Rules:** Healthcare, finance, etc. have different risk profiles
4. **Confidence Scores:** Indicate certainty level for each finding

### Monitoring
- Track risk level distribution over time
- Monitor false-positive rate
- Collect user feedback on accuracy

---

## Conclusion

The risk classification system now correctly distinguishes between:
- **Low Risk:** Secure, well-specified prompts with good hygiene
- **Medium Risk:** Acceptable shortcuts with moderate concerns
- **High Risk:** Dangerous practices requiring immediate attention

This fix eliminates the "everything is High Risk" problem while maintaining security rigor for genuinely dangerous prompts. The regression test suite ensures this behavior persists across future changes.

**Status:** ✅ COMPLETE - All requirements met, all tests passing
