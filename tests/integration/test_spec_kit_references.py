#!/usr/bin/env python3
"""
Guardrail script to prevent accidental direct references to spec-kit.

This script ensures that spec-kit is only referenced in approved locations:
- The spec-kit/ directory itself
- orchestrator/spec_kit_adapter.py (the official adapter)
- Test files specifically for spec-kit integration
- Documentation files

Usage:
    python3 test_spec_kit_references.py

Exit codes:
    0 - All references are in approved locations
    1 - Unauthorized references found
"""
import os
import re
import sys
from pathlib import Path


# Patterns to search for (only for the NEW spec-kit, not dev-spec-kit)
SPEC_KIT_PATTERNS = [
    r'\bspec-kit\b(?!-local)',  # Match 'spec-kit' but not 'spec-kit-local'
    r'\bspec_kit\b',             # Match 'spec_kit' (not dev_spec_kit or devspec)
    r'from\s+spec[_-]kit',       # Match imports from spec-kit/spec_kit
    r'import\s+spec[_-]kit',     # Match imports of spec-kit/spec_kit
]

# Patterns to EXCLUDE (these are legitimate existing references)
EXCLUDE_PATTERNS = [
    r'\bdev-spec-kit\b',        # Our existing security analyzer
    r'\bdev_spec_kit\b',
    r'\bdevspec\b',
]

# Allowed locations for spec-kit references
ALLOWED_PATHS = [
    'spec-kit/',                           # The spec-kit submodule itself
    'orchestrator/spec_kit_adapter.py',    # The official adapter
    'orchestrator/pipeline.py',            # Main pipeline that calls the adapter
    'orchestrator/models.py',              # Data models need spec-kit response fields
    'test_spec_kit_references.py',         # This guardrail script
    'test_spec_kit_integration.py',        # Integration tests
    'test_spec_kit_additive.py',           # Additive integration tests
    'verify_integration.py',               # Final verification script
    '.gitmodules',                         # Git submodule config
]

# File patterns to check
FILE_EXTENSIONS = ['.py', '.sh', '.js', '.ts', '.md', '.txt', '.yml', '.yaml', '.json']

# Directories to skip
SKIP_DIRS = {
    '.git',
    '__pycache__',
    'node_modules',
    '.pytest_cache',
    'venv',
    'env',
    'spec-kit',  # Don't check inside spec-kit itself
    'ui/node_modules',
    'ui/dist',
}


def is_allowed_path(file_path: str) -> bool:
    """Check if a file path is in the allowed list."""
    for allowed in ALLOWED_PATHS:
        if file_path.startswith(allowed) or file_path.endswith(allowed):
            return True
    return False


def is_documentation(file_path: str) -> bool:
    """Check if a file is documentation (markdown, txt in docs, README, etc.)."""
    if file_path.endswith('.md') or 'README' in file_path or 'docs/' in file_path:
        return True
    return False


def check_file(file_path: Path, repo_root: Path) -> list[tuple[str, int, str]]:
    """
    Check a file for spec-kit references.
    
    Returns:
        List of (file_path, line_number, line_content) tuples for violations
    """
    violations = []
    relative_path = str(file_path.relative_to(repo_root))
    
    # Skip allowed paths
    if is_allowed_path(relative_path):
        return violations
    
    # Documentation is allowed to mention spec-kit
    if is_documentation(relative_path):
        return violations
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Skip lines that match exclude patterns (legitimate existing references)
                if any(re.search(exclude, line, re.IGNORECASE) for exclude in EXCLUDE_PATTERNS):
                    continue
                    
                for pattern in SPEC_KIT_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((relative_path, line_num, line.strip()))
                        break
    except Exception as e:
        print(f"Warning: Could not read {relative_path}: {e}", file=sys.stderr)
    
    return violations


def scan_repository(repo_root: Path) -> list[tuple[str, int, str]]:
    """
    Scan the repository for unauthorized spec-kit references.
    
    Returns:
        List of all violations found
    """
    all_violations = []
    
    for root, dirs, files in os.walk(repo_root):
        # Remove skip directories from dirs list (modifies in-place)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for filename in files:
            # Only check relevant file types
            if not any(filename.endswith(ext) for ext in FILE_EXTENSIONS):
                continue
            
            file_path = Path(root) / filename
            violations = check_file(file_path, repo_root)
            all_violations.extend(violations)
    
    return all_violations


def main():
    """Main entry point."""
    print("="*80)
    print("SPEC-KIT REFERENCE GUARDRAIL CHECK")
    print("="*80)
    
    repo_root = Path(__file__).parent
    print(f"\nScanning repository: {repo_root}")
    print(f"Allowed reference locations:")
    for allowed in ALLOWED_PATHS:
        print(f"  ✓ {allowed}")
    print()
    
    violations = scan_repository(repo_root)
    
    if not violations:
        print("✅ PASS: No unauthorized spec-kit references found")
        print("\nAll references are properly isolated through the adapter layer.")
        return 0
    
    print(f"❌ FAIL: Found {len(violations)} unauthorized spec-kit reference(s)\n")
    
    for file_path, line_num, line_content in violations:
        print(f"  {file_path}:{line_num}")
        print(f"    {line_content}")
        print()
    
    print("="*80)
    print("VIOLATION DETECTED")
    print("="*80)
    print("\nspec-kit references must only appear in:")
    for allowed in ALLOWED_PATHS:
        print(f"  • {allowed}")
    print("\nOr in documentation files (*.md, README, docs/)")
    print("\nAll other code must use orchestrator/spec_kit_adapter.py")
    print("="*80)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
