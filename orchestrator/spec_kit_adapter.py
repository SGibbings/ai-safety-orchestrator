"""
Adapter layer for GitHub's official spec-kit integration.

This module provides a controlled interface to spec-kit functionality,
ensuring all usage goes through a single, well-defined API.

NOTE: spec-kit is a spec-driven development workflow tool, NOT a security analyzer.
It is fundamentally different from dev-spec-kit (our security rules engine).

This adapter exists to fulfill integration requirements but spec-kit does NOT
provide security analysis capabilities comparable to dev-spec-kit.

Usage is opt-in via environment variable: USE_SPEC_KIT=true
"""
import subprocess
import os
import json
import re
from typing import Dict, Any, Optional, Tuple
from .models import DevSpecFinding, SpecKitStructure


def extract_spec_structure(prompt: str, raw_output: str) -> SpecKitStructure:
    """
    Extract structured spec elements from the prompt and spec-kit output.
    
    This parses the developer prompt to identify key spec components like
    features, entities, flows, configuration, etc.
    
    Args:
        prompt: The developer prompt to analyze
        raw_output: Raw output from spec-kit
        
    Returns:
        SpecKitStructure with categorized elements
    """
    structure = SpecKitStructure()
    prompt_lower = prompt.lower()
    
    # Extract features (things the system should do)
    feature_patterns = [
        r'implement\s+([^.\n]+)',
        r'build\s+(?:a|an)\s+([^.\n]+)',
        r'create\s+(?:a|an)\s+([^.\n]+)',
        r'add\s+(?:a|an)\s+([^.\n]+)',
        r'feature[s]?:\s*([^.\n]+)',
        r'requirement[s]?:\s*([^.\n]+)'
    ]
    
    for pattern in feature_patterns:
        matches = re.finditer(pattern, prompt_lower, re.MULTILINE)
        for match in matches:
            feature = match.group(1).strip()
            if len(feature) > 5 and len(feature) < 100:  # Reasonable length
                structure.features.append(feature)
    
    # Extract entities (data models, objects)
    entity_patterns = [
        r'\b(user|admin|account|session|token|profile|dashboard|api|endpoint|database|table|model)\b',
        r'entity[:\s]+([^.\n]+)',
        r'model[:\s]+([^.\n]+)'
    ]
    
    entities_found = set()
    for pattern in entity_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            if match.lastindex and match.lastindex >= 1:
                entity = match.group(1).strip()
            else:
                entity = match.group(0).strip()
            if entity and len(entity) < 30:
                entities_found.add(entity)
    
    structure.entities = sorted(list(entities_found))
    
    # Extract flows (login, logout, workflows)
    flow_patterns = [
        r'\b(login|logout|sign\s*in|sign\s*out|authentication|authorization|register|signup)\b',
        r'\b(create|read|update|delete|crud)\b',
        r'flow[:\s]+([^.\n]+)',
        r'workflow[:\s]+([^.\n]+)'
    ]
    
    flows_found = set()
    for pattern in flow_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            if match.lastindex and match.lastindex >= 1:
                flow = match.group(1).strip()
            else:
                flow = match.group(0).strip()
            if flow and len(flow) < 50:
                flows_found.add(flow)
    
    structure.flows = sorted(list(flows_found))
    
    # Extract configuration mentions
    config_patterns = [
        r'(jwt\s+secret|api\s+key|database\s+url|connection\s+string|environment\s+variable)',
        r'config[uration]*[:\s]+([^.\n]+)',
        r'\.env|environment\s+variables?',
        r'secret[s]?|credential[s]?|key[s]?'
    ]
    
    for pattern in config_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            if match.lastindex and match.lastindex >= 1:
                config = match.group(1).strip()
            else:
                config = match.group(0)
            if config and len(config) < 80:
                structure.configuration.append(config)
    
    # Extract error handling mentions
    error_patterns = [
        r'error\s+handling',
        r'exception\s+handling',
        r'fallback',
        r'retry',
        r'graceful\s+degradation',
        r'error\s+response',
        r'try\s*[/-]\s*catch'
    ]
    
    for pattern in error_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            structure.error_handling.append(match.group(0))
    
    # Extract testing mentions
    testing_patterns = [
        r'test[ing]*\s+(?:strategy|plan|suite|cases?)',
        r'unit\s+test',
        r'integration\s+test',
        r'e2e\s+test',
        r'test\s+coverage',
        r'automated\s+test'
    ]
    
    for pattern in testing_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            structure.testing.append(match.group(0))
    
    # Extract logging mentions
    logging_patterns = [
        r'log[ging]*',
        r'observability',
        r'monitoring',
        r'metrics',
        r'telemetry',
        r'audit\s+log'
    ]
    
    for pattern in logging_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            structure.logging.append(match.group(0))
    
    # Extract authentication mentions
    auth_patterns = [
        r'oauth[2]?',
        r'jwt|json\s+web\s+token',
        r'session[s]?',
        r'authentication',
        r'authorization',
        r'sso|single\s+sign[- ]on',
        r'role[s]?[- ]based',
        r'rbac'
    ]
    
    for pattern in auth_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            structure.authentication.append(match.group(0))
    
    # Extract data storage mentions
    storage_patterns = [
        r'database|postgres|mysql|mongodb',
        r'redis|cache',
        r'storage|persist',
        r'sql|nosql'
    ]
    
    for pattern in storage_patterns:
        matches = re.finditer(pattern, prompt_lower)
        for match in matches:
            structure.data_storage.append(match.group(0))
    
    # Deduplicate and clean up
    structure.features = list(dict.fromkeys(structure.features))[:10]  # Limit to 10
    structure.configuration = list(dict.fromkeys(structure.configuration))[:10]
    structure.error_handling = list(dict.fromkeys(structure.error_handling))[:5]
    structure.testing = list(dict.fromkeys(structure.testing))[:5]
    structure.logging = list(dict.fromkeys(structure.logging))[:5]
    structure.authentication = list(dict.fromkeys(structure.authentication))[:10]
    structure.data_storage = list(dict.fromkeys(structure.data_storage))[:10]
    
    return structure


class SpecKitAdapter:
    """
    Adapter for GitHub's spec-kit CLI tool.
    
    This class provides a controlled interface to spec-kit, isolating
    direct dependencies on the spec-kit repository structure.
    """
    
    def __init__(self, spec_kit_path: Optional[str] = None):
        """
        Initialize the spec-kit adapter.
        
        Args:
            spec_kit_path: Path to spec-kit installation. If None, uses default.
        """
        if spec_kit_path is None:
            # Default to spec-kit/ in repository root
            spec_kit_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "spec-kit"
            )
        
        self.spec_kit_path = spec_kit_path
        self.cli_script = os.path.join(spec_kit_path, "src", "specify_cli", "__init__.py")
        
    def is_available(self) -> bool:
        """
        Check if spec-kit is available and properly configured.
        
        Returns:
            True if spec-kit can be used, False otherwise.
        """
        return os.path.exists(self.cli_script)
    
    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        Check if all prerequisites for spec-kit are met.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_available():
            return False, f"spec-kit CLI not found at {self.cli_script}"
        
        # Check if required dependencies are available
        try:
            import typer
            import rich
            return True, "spec-kit prerequisites satisfied"
        except ImportError as e:
            return False, f"Missing spec-kit dependency: {e.name}"
    
    def run_check(self, project_path: str) -> Dict[str, Any]:
        """
        Run spec-kit check command on a project.
        
        NOTE: spec-kit's 'check' validates spec-driven development workflow,
        not security issues. This is fundamentally different from dev-spec-kit.
        
        Args:
            project_path: Path to project to check
            
        Returns:
            Dict with check results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "spec-kit not available",
                "findings": []
            }
        
        try:
            result = subprocess.run(
                ["python3", self.cli_script, "check"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "spec-kit check timed out",
                "findings": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "findings": []
            }
    
    def analyze_prompt(self, prompt: str) -> Tuple[str, list[DevSpecFinding], int, Optional[SpecKitStructure]]:
        """
        Analyze a developer prompt using spec-kit.
        
        IMPORTANT: This method exists for API compatibility but spec-kit
        does NOT perform security analysis. It cannot replace dev-spec-kit's
        security scanning capabilities.
        
        This extracts structured spec elements from the prompt to help users
        understand their project structure before seeing security findings.
        
        Args:
            prompt: Developer prompt to analyze
            
        Returns:
            Tuple of (raw_output, findings, exit_code, structure)
        """
        # spec-kit is not a security analyzer - it's a workflow tool
        warning = (
            "spec-kit analysis: Extracting spec structure from prompt.\n"
            "This provides workflow insights, not security analysis.\n"
        )
        
        # Extract structured spec elements from the prompt
        structure = extract_spec_structure(prompt, warning)
        
        return warning, [], 0, structure


def should_use_spec_kit() -> bool:
    """
    Determine if spec-kit should be used based on environment configuration.
    
    Returns:
        True if spec-kit should be used, False for default dev-spec-kit behavior
    """
    return os.getenv("USE_SPEC_KIT", "").lower() in ("true", "1", "yes")


def get_adapter() -> Optional[SpecKitAdapter]:
    """
    Get a spec-kit adapter instance if enabled.
    
    Returns:
        SpecKitAdapter instance if enabled, None otherwise
    """
    if should_use_spec_kit():
        return SpecKitAdapter()
    return None
