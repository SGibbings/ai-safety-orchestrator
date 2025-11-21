# --- Expanded Risky SQL and Shell Command Detection ---
# Risky SQL commands (WARNING)
if grep -iqE '\b(drop database|truncate|alter( table)?|drop table)\b' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_RISKY_SQL" "Prompt suggests using risky SQL commands (DROP DATABASE, TRUNCATE, ALTER, DROP TABLE)." "Avoid destructive SQL operations unless absolutely necessary and always require confirmation."
fi
# Dangerous shell commands (WARNING, but avoid false positives)
if grep -iqE '\brm[ ]+-rf[ ]+(/|\*|~|\.|[a-zA-Z0-9_/-]+)' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE '>/dev/null|git reset --hard' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_DANGEROUS_SHELL" "Prompt suggests using a dangerous shell command (e.g., rm -rf)." "Avoid destructive shell commands unless absolutely necessary."
fi
#!/usr/bin/env bash
set -euo pipefail

# --- Input Handling ---
PROMPT=""
if [[ $# -gt 0 ]]; then
  PROMPT=$(cat "$1")
else
  PROMPT=$(cat)
fi
NORMALIZED_PROMPT=$(echo "$PROMPT" | tr '\n' ' ')

# --- Rule Engine Data Structures ---
declare -A SEVERITY_COUNTS=([INFO]=0 [WARNING]=0 [ERROR]=0 [BLOCKER]=0 [BLOCKED]=0)
WARNINGS=()

add_warning() {
  local category="$1" severity="$2" code="$3" message="$4" suggestion="$5"
  SEVERITY_COUNTS[$severity]=$((SEVERITY_COUNTS[$severity]+1))
  WARNINGS+=("[$category][$severity][$code]\n$message\nSuggestion: $suggestion\n")
}

# --- RULES ---
# MD5 (WARNING only if used for password/credential storage)
if grep -iqE '\bmd5\b' <<< "$NORMALIZED_PROMPT"; then
  if grep -iqE '(md5.*(password|credential|secret|token|api[_-]?key|auth|login))|((password|credential|secret|token|api[_-]?key|auth|login).*md5)|hashed with md5' <<< "$NORMALIZED_PROMPT"; then
    add_warning "SECURITY" "WARNING" "SEC_WEAK_HASH_MD5" "Prompt suggests using md5 for password or credential storage, which is a weak hash function." "Use a strong hash function like SHA-256 or bcrypt."
  fi
fi
# http:// (WARNING)
if grep -iqE 'http://' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_INSECURE_TRANSPORT" "Prompt suggests using http://, which is insecure transport." "Always use HTTPS/TLS for all endpoints."
fi
# Skipping input validation (WARNING)
if grep -iqE 'skip input validation|no validation checks|assume safe input' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_SKIP_VALIDATION" "Prompt suggests skipping or omitting input validation." "Always validate and sanitize all user input."
fi
# Frontend-only validation (WARNING)
if grep -iqE 'validation (is|only|done) (on|in) the frontend|frontend-only validation|only validate on the frontend|validation is only done on the frontend' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_FRONTEND_ONLY_VALIDATION" "Prompt suggests validation is only performed on the frontend, not the backend." "Always perform input validation on the backend/server as well."
fi
# Exposing internal state or sessions (BLOCKED, only if not explicitly avoided)
if grep -iqE '/dump|return all session tokens|full application state|dump state|dump memory|dump env' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'do not expose internal state|never expose internal state|sanitize logs|use environment variables' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_EXPOSE_SESSIONS" "Prompt suggests exposing internal state, session tokens, or full application state." "Never expose internal state or session tokens in any endpoint."
fi
# GET endpoint for login (INFO)
## GET endpoint for login (INFO, not WARNING or BLOCKED)
if grep -iqE 'GET[ ]+/[a-zA-Z0-9_-]*login' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "INFO" "SEC_GET_LOGIN_ENDPOINT" "Prompt suggests using a GET endpoint for login (e.g., /admin-login)." "Login endpoints should use POST, not GET."
fi
# Skipping authentication (BLOCKED)
if grep -iqE 'no need for auth|skip authentication' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_SKIP_AUTH" "Prompt suggests skipping authentication or saying no need for auth." "Never skip authentication for sensitive operations."
fi
# Hardcoded JWT secrets (BLOCKED, only if not explicitly avoided)
## Hardcoded JWT/Secret/Token/API Key (BLOCKED, only if not explicitly avoided and only if assigned a quoted value)
if grep -iqE '((jwt(_secret)?|token|api[_-]?key|secret|password)[ ]*=[ ]*["'"'][^"'"']+["'"'])' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'use environment variables|never hard-code secrets|do not hard-code secrets' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_HARDCODED_JWT_SECRET" "Prompt suggests hardcoding a JWT secret, token, API key, or password as a quoted literal or assignment." "Never hard-code JWT secrets, API keys, or passwords; always use environment variables or secret managers."
fi
# Exposing internal state (BLOCKED, only if not explicitly avoided)
if grep -iqE 'expos(e|ing) (debug|internal state|state snapshot|internal data|all variables|all state|full dump|full log|last [0-9]+ events|dump state|dump memory|dump env)' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'do not expose internal state|never expose internal state|sanitize logs|use environment variables' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_EXPOSE_INTERNAL_STATE" "Prompt suggests exposing debug data, internal state, or returning large logs (e.g., last 100 events, state snapshot)." "Never expose internal state, debug data, or large logs in production or to untrusted users."
fi
# Avoiding security (BLOCKED)
if grep -iqE 'skip security|ignore auth|no security checks|disable security|bypass auth|no auth needed|no authentication needed|remove security|turn off security' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_AVOID_SECURITY" "Prompt suggests skipping or avoiding security/authentication checks." "Never skip or disable security/authentication in production systems."
fi
# Ambiguous database instructions (WARNING)
if grep -iqE 'connect to any database|whatever works|usual stuff|any db|any database|pick a database|choose a database|use whichever|use whatever|first one that works' <<< "$NORMALIZED_PROMPT"; then
  add_warning "ARCH" "WARNING" "ARCH_AMBIGUOUS_DB" "Prompt contains ambiguous or vague database instructions (e.g., connect to any database, whatever works)." "Specify a single, well-defined database technology and configuration."
fi
# Rule: Exception handling (BLOCKED)
if grep -iqE 'try[ ]*\{|try[ ]*:' <<< "$NORMALIZED_PROMPT" || grep -iqE 'except[ ]*\{|except[ ]*:' <<< "$NORMALIZED_PROMPT" || grep -iqE 'catch[ ]*\{|catch[ ]*:' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_EXCEPTION_HANDLING" "Prompt suggests using exception handling (try/catch/except) in a way that may hide errors or security issues." "Avoid using exception handling to suppress or hide errors, especially in security-sensitive code."
fi
# Rule: Hardcoded user IDs (BLOCKED)
if grep -iqE 'user[ _-]?id[ =:]+[0-9]+' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_HARDCODED_USERID" "Prompt suggests hardcoding a user ID (e.g., user_id = 12345)." "Never hardcode user IDs; always use dynamic, authenticated user context."
fi
# Rule: Hard-coded secret or password (BLOCKED, only if not explicitly avoided)
## Hard-coded secret or password (BLOCKED, only if not explicitly avoided and only if assigned a quoted value)
if grep -iqE '((secret|password|key|token|credential)[ ]*=[ ]*["'"'][^"'"']+["'"'])' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'use environment variables|never hard-code secrets|do not hard-code secrets' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKED" "SEC_HARDCODED_SECRET" "Prompt suggests hard-coding a secret, password, or credential as a quoted assignment (e.g., password = \"abc\")." "Never hard-code secrets; always use environment variables or secret managers."
fi
# Debug endpoints (/dump, /debug, /internal, /state, etc. as WARNING for exposing internal state)
if grep -iqE '/(dump|debug|internal|state|vars|env|memory|log|snapshot)' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'do not expose internal state|never expose internal state|sanitize logs|use environment variables' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_DEBUG_ENDPOINT" "Prompt suggests exposing a debug or internal endpoint (e.g., /dump, /debug, /internal, /state, etc.)." "Do not expose debug or internal endpoints in production."
fi
# ...existing rules from the original script...
# For brevity, you would copy all the other rules from the original script here, unchanged.

# --- Output ---
TOTAL=${#WARNINGS[@]}
INFO=${SEVERITY_COUNTS[INFO]:-0}
WARNING=${SEVERITY_COUNTS[WARNING]:-0}
ERROR=${SEVERITY_COUNTS[ERROR]:-0}
BLOCKER=${SEVERITY_COUNTS[BLOCKER]:-0}
BLOCKED=${SEVERITY_COUNTS[BLOCKED]:-0}

echo "Security Issue Summary:"
for warning in "${WARNINGS[@]}"; do
  echo -e "$warning"
done

if [ "$BLOCKED" -gt 0 ]; then
  echo "❌ BLOCKED: Prompt contains critical security risks and will not be submitted."
  exit 99
elif [ "$BLOCKER" -gt 0 ]; then
  exit 2
elif [ "$ERROR" -gt 0 ]; then
  exit 1
elif [ "$WARNING" -gt 0 ] || [ "$INFO" -gt 0 ]; then
  echo "⚠️  Edits recommended: Issues detected. Please review warnings before proceeding."
  exit 1
else
  echo "✅ All good: No problems detected."
  exit 0
fi
