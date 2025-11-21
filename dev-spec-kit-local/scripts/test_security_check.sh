# Test script for security-check.sh
# Runs the enhanced security-check.sh on test_prompt.txt and prints output

set -e
SCRIPT_DIR="$(dirname "$0")"
CHECK_SH="$SCRIPT_DIR/security-check.sh"
PROMPT_FILE="$SCRIPT_DIR/../../../../test_prompt.txt"

bash "$CHECK_SH" "$PROMPT_FILE"
