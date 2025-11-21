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
declare -A SEVERITY_COUNTS=([INFO]=0 [WARNING]=0 [ERROR]=0 [BLOCKER]=0)
WARNINGS=()

add_warning() {
  local category="$1" severity="$2" code="$3" message="$4" suggestion="$5"
  SEVERITY_COUNTS[$severity]=$((SEVERITY_COUNTS[$severity]+1))
  WARNINGS+=("[$category][$severity][$code]\n$message\nSuggestion: $suggestion\n")
}

# --- RULES ---
# Example: SEC_UNAUTH_DELETE
if grep -iqE 'delete.*user.*(without.*auth|no.*auth|no authentication|unauthenticated)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_UNAUTH_DELETE" "Detected an endpoint that deletes users by email without authentication." "Require authenticated admin role and proper access control before deletion."
fi
if grep -iqE 'admin.*(auto-?create|regenerat|backdoor|without.*auth|no.*auth|hardcoded|hard-coded|default|built-in)|(hardcoded|hard-coded|default|built-in).*(admin.*user|admin.*account)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_ADMIN_BACKDOOR" "Detected hardcoded, default, or unauthenticated admin user." "Require secure admin creation with strong authentication."
fi
# JWT/token storage in files - only flag if actually storing tokens in files, not just using JWT
if grep -iqE '(save|store|write|persist).*(JWT|token).*(file|json.*file|\.json)|JWT.*(saved|stored|written).*(file|json)' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'JWT.*(access token|signing key|secret).*(environment|env var|config)|environment.*JWT|env var.*JWT' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_INSECURE_JWT_STORAGE" "Prompt suggests storing JWTs or tokens in a file (e.g., JSON)." "Use secure server-side storage or a proper session store."
fi
if grep -iqE 'wipe.*db|database.*wipe|reset.*db|regenerat.*admin.*restart' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DB_WIPE_ON_RESTART" "Prompt suggests wiping the database and regenerating admin user on restart." "Never wipe production data on restart; require explicit admin action."
fi
if grep -iqE 'express' <<< "$NORMALIZED_PROMPT" && grep -iqE 'fastapi' <<< "$NORMALIZED_PROMPT" && (grep -iqE 'service' <<< "$NORMALIZED_PROMPT" || grep -iqE 'microservice' <<< "$NORMALIZED_PROMPT"); then
  add_warning "ARCH" "WARNING" "ARCH_CONFLICTING_FRAMEWORKS" "Prompt mentions both Express (Node.js) and FastAPI (Python) in the same service or microservice." "Choose a single backend framework and language for this service."
fi
if grep -iqE 'use (either|any|whichever|the fastest|combine).*flask.*next\.js|django.*laravel.*express' <<< "$NORMALIZED_PROMPT"; then
  add_warning "ARCH" "WARNING" "ARCH_VAGUE_TECH_CHOICE" "Prompt is vague about technology/framework choice (e.g., Flask, Next.js, Django, Laravel, Express)." "Specify a single technology stack for clarity."
fi
if grep -iqE 'raw html' <<< "$NORMALIZED_PROMPT" && grep -iqE 'jquery' <<< "$NORMALIZED_PROMPT" && grep -iqE 'login' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_INSECURE_LOGIN_UI" "Prompt uses raw HTML and jQuery for login/auth flows without secure handling." "Use secure frontend frameworks and implement CSRF protection and HTTPS."
fi
# Only flag if auth is mentioned AND there's explicit mention of HTTP without HTTPS
if grep -iqE 'http://' <<< "$NORMALIZED_PROMPT" \
  && (grep -iqE 'login|auth|jwt|token|password' <<< "$NORMALIZED_PROMPT") \
  && ! grep -iqE 'https|tls|behind.*nginx|nginx.*handle.*tls|proxy.*handle.*https' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_NO_TLS_FOR_AUTH" "HTTP mentioned for authentication without HTTPS/TLS or reverse proxy." "Always use HTTPS/TLS for login/auth endpoints."
fi
# --- New rules for advanced prompts ---
if grep -iqE 'download.*(image|file|content|data).*without authentication' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_UNAUTH_DOWNLOAD" "Detected unauthenticated download of user content (e.g., images, files, data)." "Require authentication for all download endpoints."
fi
if grep -iqE 'store.*upload.*(/tmp|tmp/)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_INSECURE_TMP_STORAGE" "Prompt suggests storing user uploads in /tmp or a temporary directory long-term." "Store uploads in a secure, persistent location."
fi
if grep -iqE 'return.*stack trace.*(response|api|client)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_STACKTRACE_IN_RESPONSE" "Prompt suggests returning stack traces directly in API responses." "Never expose stack traces to clients; log them securely."
fi
# Financial operations without authentication - must have both "no auth" AND financial keywords
if grep -iqE '(no need for authentication|no authentication required|no auth|skip.*auth).*(financ|transaction|payment|balance|bank|invoice|billing)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_NO_AUTH_FINANCIAL" "Detected financial operation without authentication." "Require authentication for all financial endpoints."
fi
if grep -iqE 'adjust.*balance.*no validation' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_UNVALIDATED_BALANCE_ADJUST" "Detected unvalidated balance adjustment endpoint." "Validate all balance changes and require proper authorization."
fi
if grep -iqE "debug.*(dump|print|show).*(in-memory|environment variable|env var|all variables)" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DEBUG_DUMP_ENV" "Prompt suggests a debug endpoint that dumps in-memory state or environment variables." "Never expose internal state or environment variables in any endpoint."
fi
if grep -iqE 'run.*docker.*as root|run.*as root.*file permission' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_DOCKER_RUNS_AS_ROOT" "Prompt suggests running Docker containers as root to avoid file permission issues." "Run containers as non-root users for security."
fi
if grep -iqE "don['\"]?t use https|no https needed|no tls needed|behind a firewall.*no https" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_EXPLICIT_NO_TLS" "Prompt explicitly disables HTTPS/TLS for sensitive services." "Always use HTTPS/TLS for all services, even behind firewalls."
fi
# Secrets in config files (ERROR - should use env vars but not as bad as hardcoded in code)
if grep -iqE "(secret|jwt_secret|api.*key|token).*(stored|store|in|from).*config\.json|config\.json.*(secret|jwt_secret|api.*key|token)" <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'not.*config\.json|don'\''t.*config\.json|avoid.*config\.json' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_SECRETS_IN_CONFIG_FILE" "Prompt suggests storing secrets in config.json file." "Use environment variables or secret managers for secrets."
fi
# Debug endpoints dumping configuration or settings (BLOCKER)
if grep -iqE "/debug.*(dump|dumps|show|shows|print|prints|return|returns).*(config|configuration|settings|django.*settings|app.*settings|env|environment)" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DEBUG_DUMPS_CONFIG" "Prompt suggests a /debug endpoint that dumps application configuration or settings." "Never expose configuration, settings, or environment variables in debug endpoints."
elif grep -iqE "/debug.*(dump|show|print).*(token|credential|connection string|env var|environment variable|password|session)" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_INSECURE_DEBUG_ENDPOINT" "Prompt suggests a /debug endpoint that dumps tokens, credentials, or environment variables." "Never expose sensitive data in debug endpoints."
fi
if grep -iqE "kafka.*rabbitmq.*redis|rabbitmq.*kafka.*redis|redis.*kafka.*rabbitmq" <<< "$NORMALIZED_PROMPT"; then
  add_warning "ARCH" "WARNING" "ARCH_OVERLOADED_MESSAGE_BROKERS" "Prompt suggests running Kafka, RabbitMQ, and Redis Pub/Sub in a single service." "Separate message brokers into dedicated services."
fi
if grep -iqE 'choose.*database.*at runtime.*first.*connect' <<< "$NORMALIZED_PROMPT"; then
  add_warning "ARCH" "ERROR" "ARCH_DYNAMIC_DB_SELECTION" "Prompt suggests choosing the database at runtime by whichever connects first." "Explicitly configure the database to use."
fi
if grep -iqE "patient record.*json file.*no encryption|required yet" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_PHI_IN_PLAINTEXT_FILE" "Prompt suggests storing medical/patient data in plaintext files without encryption." "Encrypt all PHI and sensitive data at rest."
fi
if grep -iqE "/export.*all.*data.*no authentication|required" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_UNAUTH_DATA_EXPORT" "Prompt suggests an unauthenticated export endpoint for all patient or sensitive data." "Require authentication and strict access control for all export endpoints."
fi
if grep -iqE 'drop.*recreate.*all data.*on startup|quickstart.*drop.*recreate.*data' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DROP_ALL_DATA_ON_START" "Prompt suggests dropping and recreating all data on startup." "Never drop production data automatically; require explicit admin action."
fi
# Plain text password storage
if grep -iqE 'plain.?text.*password|password.*plain.?text|store.*password.*(unencrypted|raw|directly)|save.*password.*(plain|clear)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_PLAINTEXT_PASSWORDS" "Prompt suggests storing passwords in plain text." "Always hash passwords with bcrypt, Argon2, or PBKDF2 before storage."
fi
# Logging passwords (raw/plaintext)
if grep -iqE 'log.*(raw|plaintext|actual|plain text|clear text).*(password|credentials)|log.*(request payload|request body|full request).*(password|credentials)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE '(password|credentials).*(log|logged|logging).*(raw|plaintext|plain text|clear|request payload)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_LOGS_PASSWORDS" "Prompt suggests logging raw/plaintext passwords." "Never log passwords or credentials; log only sanitized request metadata."
fi
# Logging PII (emails, names, etc.) - ERROR severity
if grep -iqE 'log.*(email address|user.*email|customer.*email)|email.*(logged|log|logging)' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'do not log.*email|never log.*email|avoid logging.*email|without.*email' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_LOGS_PII_EMAIL" "Prompt suggests logging user email addresses (PII)." "Avoid logging PII; use anonymized identifiers or pseudonymized data for debugging."
fi
# Hardcoded secrets/credentials (only if NOT using env vars or secret management)
if grep -iqE 'hardcode.*(secret|key|password|token|credential)|secret.*["\x27][a-zA-Z0-9_-]{6,}["\x27]|jwt.*secret.*["\x27]|api.*key.*["\x27]' <<< "$NORMALIZED_PROMPT" \
  && ! grep -iqE 'environment variable|env var|secret manager|from env|getenv|process\.env|os\.environ' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_HARDCODED_SECRET" "Prompt suggests hardcoding secrets, API keys, or credentials." "Use environment variables or secret management systems."
fi
# Use HTTP explicitly when auth is involved
if grep -iqE 'use http|http instead|http because|http only' <<< "$NORMALIZED_PROMPT" && (grep -iqE 'login|auth|password|token|credential' <<< "$NORMALIZED_PROMPT"); then
  add_warning "SECURITY" "BLOCKER" "SEC_HTTP_FOR_AUTH" "Prompt explicitly uses HTTP instead of HTTPS for authentication." "Always use HTTPS for authentication and sensitive data."
fi
# Skip/missing input validation (only if explicitly skipping, not just not mentioned)
if grep -iqE 'skip (input )?validation|no (input )?validation|assume (input )?safe|trust (client|frontend) input|validation.*not needed' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_MISSING_INPUT_VALIDATION" "Prompt suggests skipping input validation on the backend." "Always validate and sanitize input on the server side, never trust client input."
fi
# MD5 for security purposes
if grep -iqE 'md5.*(hash|password|email|security|encrypt)|(hash|encrypt).*(md5)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_WEAK_HASH_MD5" "Prompt suggests using MD5 for security-sensitive hashing." "Use SHA-256, SHA-3, or bcrypt/Argon2 for passwords. MD5 is cryptographically broken."
fi
# SHA-256 for password hashing (better than MD5 but worse than bcrypt/Argon2)
# Check for SHA-256 being used for password hashing (not just mentioned as "not using it")
if grep -iqE '(password|hash).*(using|with|use).*(sha-?256|sha256)|(sha-?256|sha256).*(for|to hash).*(password)' <<< "$NORMALIZED_PROMPT" \
  || (grep -iqE 'sha-?256' <<< "$NORMALIZED_PROMPT" && grep -iqE 'password.*hash|hash.*password' <<< "$NORMALIZED_PROMPT" && ! grep -iqE 'not.*sha-?256|instead of.*sha-?256|don'\''t use.*sha-?256|avoid.*sha-?256' <<< "$NORMALIZED_PROMPT"); then
  add_warning "SECURITY" "ERROR" "SEC_WEAK_PASSWORD_HASH_SHA256" "Prompt suggests using SHA-256 for password hashing." "Use bcrypt, Argon2, or PBKDF2 for password hashing. SHA-256 is too fast and vulnerable to brute-force attacks."
fi
# Debug endpoint exposing sensitive data (only actual secrets, not IDs/emails/filenames)
# Pattern must match: /debug FOLLOWED BY "returns X" where X is a secret type
# Use more restrictive matching to avoid false positives from "no raw tokens" mentions
if grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes|dump|dumps)\s+(all |the |last [0-9]+ )?(token|session|credential|password|secret|api.*key|jwt|env|environment)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug endpoint\s+(return|returns|show|shows|expose|exposes|dump|dumps)\s+(all |the |last [0-9]+ )?(token|session|credential|password|secret|api.*key|jwt|env|environment)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DEBUG_EXPOSES_SECRETS" "Prompt suggests a debug endpoint that exposes tokens, credentials, passwords, or secrets." "Never expose sensitive data in debug endpoints; use secure logging instead."
# Debug endpoint exposing PII (emails) - ERROR severity
elif grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes)\s+(all |the |last [0-9]+ )?email' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug.*(return|returns|show|shows|expose|exposes)\s+(all |the |last [0-9]+ )?email' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_DEBUG_EXPOSES_PII" "Prompt suggests a debug endpoint that exposes emails (PII)." "Never expose personally identifiable information in debug endpoints."
# Debug endpoint exposing large amounts of metadata (100+) - BLOCKER (significant data leak)
elif grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes)\s+.{0,50}(last |all )?([1-9][0-9]{2,})\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug.*(return|returns|show|shows|expose|exposes).{0,50}(for )?(last |all )?([1-9][0-9]{2,})\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_DEBUG_EXPOSES_BULK_DATA" "Prompt suggests a debug endpoint that exposes large amounts of user data (100+ records)." "Never expose bulk user data in debug endpoints; this is a significant data leak risk."
# Debug endpoint exposing moderate amounts of metadata (50-99) - ERROR
elif grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes)\s+.{0,50}(last |all )?([5-9][0-9])\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug.*(return|returns|show|shows|expose|exposes).{0,50}(for )?(last |all )?([5-9][0-9])\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_DEBUG_EXPOSES_BULK_METADATA" "Prompt suggests a debug endpoint that exposes moderate amounts of user data (50-99 records)." "Minimize data exposure in debug endpoints; use proper admin interfaces with authentication."
# Debug endpoint exposing small-to-moderate amounts (10-49) - ERROR (privacy risk)
elif grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes)\s+.{0,50}(last |all )?([1-4][0-9])\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug.*(return|returns|show|shows|expose|exposes).{0,50}(for )?(last |all )?([1-4][0-9])\+?\s+(user|id|filename|file.*name|record|upload)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_DEBUG_EXPOSES_MULTIPLE_IDS" "Prompt suggests a debug endpoint that exposes multiple user IDs (10-49 records)." "Debug endpoints should not expose user data even in small batches; use proper admin interfaces with authentication."
# Debug endpoint exposing small amounts of metadata (IDs, filenames) - WARNING only
elif grep -iqE '/debug[^ ]*\s+(return|returns|show|shows|expose|exposes)\s+(all |the |last [0-9]+ )?(user|id|filename|file.*name)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'debug.*(return|returns|show|shows|expose|exposes)\s+(all |the |last [0-9]+ )?(user|id|filename|file.*name)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_DEBUG_EXPOSES_METADATA" "Prompt suggests a debug endpoint that exposes user IDs or filenames." "Minimize data exposure in debug endpoints and disable them in production."
fi
# No authentication on internal endpoints
# Very specific pattern: only trigger when explicitly saying "no auth" or "skip auth" on "internal endpoints"
# Avoid false positives with gateway header trust scenarios (covered by SEC_TRUSTS_GATEWAY_HEADER)
if grep -iqE '(no need for|skip|skipping|bypass).*(auth|authentication).*(on )?(internal|private).*endpoint' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE '(internal|private).*endpoint.*(no|without|skip).*(auth|authentication).*check' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE 'network.*(is )?(secure|safe).*enough.*(no|without|skip)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE '(no|skip).*(auth|authentication).*(internal|private).*endpoint.*(network|firewall)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_NO_AUTH_INTERNAL" "Prompt suggests skipping authentication on internal endpoints assuming network security." "Always require authentication; network-level security is insufficient."
fi
# GET endpoint for login/authentication
if grep -iqE '(get|GET).*endpoint.*(login|auth)|login.*(get|GET).*endpoint' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_GET_FOR_AUTH" "Prompt suggests using GET for login/authentication endpoints." "Use POST for authentication to prevent credentials in URLs and logs."
fi
# Trusting gateway/proxy headers without verification
if grep -iqE '(trust|trusts|use).*(x-user-id|x-authenticated-user|x-forwarded-user|x-auth-user|gateway.*header|proxy.*header)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE '(service|endpoint).*(trust|trusts|accept|accepts|use|uses).*(header|x-).*(?:passed|provided|sent).*(by gateway|by proxy|from gateway|from proxy)' <<< "$NORMALIZED_PROMPT" \
  || grep -iqE '(x-user-id|x-authenticated-user|x-forwarded-user).*(passed|provided|sent).*(by gateway|by proxy|from gateway|from proxy)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_TRUSTS_GATEWAY_HEADER" "Prompt suggests trusting user identity headers from gateway/proxy without verification." "Validate gateway headers with shared secrets or mutual TLS; untrusted headers enable impersonation attacks."
fi

# Additional WARNING-level checks for common issues
# No testing mentioned
if ! grep -iqE 'test|unit test|integration test|pytest|jest|mocha|testing' <<< "$NORMALIZED_PROMPT"; then
  add_warning "QUALITY" "WARNING" "QUAL_NO_TESTING" "No testing strategy mentioned in the spec." "Add unit tests, integration tests, or specify a testing approach."
fi
# No error handling mentioned
if ! grep -iqE 'error|exception|try.*catch|error handling|failure|fallback' <<< "$NORMALIZED_PROMPT"; then
  add_warning "QUALITY" "WARNING" "QUAL_NO_ERROR_HANDLING" "No error handling strategy mentioned in the spec." "Define how errors and exceptions will be handled and logged."
fi
# No logging/monitoring mentioned
if ! grep -iqE 'log|logging|monitor|observability|metrics|telemetry' <<< "$NORMALIZED_PROMPT"; then
  add_warning "QUALITY" "WARNING" "QUAL_NO_LOGGING" "No logging or monitoring strategy mentioned in the spec." "Add logging for debugging and monitoring for production observability."
fi
# Vague authentication plan
if grep -iqE '(auth|authentication).*(later|tbd|todo|not sure|maybe|probably|will add)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_AUTH_DEFERRED" "Authentication strategy is vague or deferred." "Define authentication approach upfront (JWT, sessions, OAuth, etc.)."
fi
# Vague database choice
if grep -iqE '(database|db).*(not sure|maybe|probably|whatever|any|either|later|tbd)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "ARCH" "WARNING" "ARCH_VAGUE_DATABASE" "Database choice is undefined or vague." "Specify database technology for proper data modeling and connection handling."
fi

# --- Output ---
TOTAL=${#WARNINGS[@]}
INFO=${SEVERITY_COUNTS[INFO]:-0}
WARNING=${SEVERITY_COUNTS[WARNING]:-0}
ERROR=${SEVERITY_COUNTS[ERROR]:-0}
BLOCKER=${SEVERITY_COUNTS[BLOCKER]:-0}

for warning in "${WARNINGS[@]}"; do
  echo -e "$warning"
done

echo "Total warnings: $TOTAL (INFO: $INFO, WARNING: $WARNING, ERROR: $ERROR, BLOCKER: $BLOCKER)"

if (( BLOCKER > 0 )); then
  exit 2
elif (( ERROR > 0 )); then
  exit 1
else
  exit 0
fi
