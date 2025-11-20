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
if grep -iqE 'admin.*(auto-?create|regenerat|backdoor|without.*auth|no.*auth)' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "BLOCKER" "SEC_ADMIN_BACKDOOR" "Detected auto-creation or unauthenticated admin user." "Require secure admin creation with strong authentication."
fi
if grep -iqE 'JWT.*file|token.*file|save.*token.*json|store.*token.*json' <<< "$NORMALIZED_PROMPT"; then
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
if (grep -iqE 'login' <<< "$NORMALIZED_PROMPT" || grep -iqE 'auth' <<< "$NORMALIZED_PROMPT" || grep -iqE 'jwt' <<< "$NORMALIZED_PROMPT" || grep -iqE 'token' <<< "$NORMALIZED_PROMPT" || grep -iqE 'password' <<< "$NORMALIZED_PROMPT") && ! grep -iqE 'https' <<< "$NORMALIZED_PROMPT" && ! grep -iqE 'tls' <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "WARNING" "SEC_NO_TLS_FOR_AUTH" "No mention of HTTPS/TLS for authentication flows." "Always use HTTPS/TLS for login/auth endpoints."
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
if grep -iqE '(no need for authentication|no authentication required|no auth).*finance|transaction|payment|balance|bank' <<< "$NORMALIZED_PROMPT"; then
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
if grep -iqE "config\.json.*repo root.*secret|store.*secret.*config\.json" <<< "$NORMALIZED_PROMPT"; then
  add_warning "SECURITY" "ERROR" "SEC_SECRETS_IN_CONFIG_FILE" "Prompt suggests storing secrets in config.json in the repo root." "Use environment variables or secret managers for secrets."
fi
if grep -iqE "/debug.*(dump|show|print).*(token|credential|connection string|env var|environment variable|password|session)" <<< "$NORMALIZED_PROMPT"; then
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
