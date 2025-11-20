#!/bin/bash
# UserPromptSubmit hook handler for security check
# This script is called by hooks.json before Claude processes a user prompt.
# It runs security-check.sh and prints warnings if any risks are detected.

SCRIPT_DIR="$(dirname "$0")/../scripts"
SECURITY_CHECK="$SCRIPT_DIR/security-check.sh"
PROMPT_FILE="$1"

if [ -f "$SECURITY_CHECK" ]; then
  bash "$SECURITY_CHECK" "$PROMPT_FILE"
fi
