#!/usr/bin/env python3
"""
Example script demonstrating how to use the AI Safety Orchestrator API
"""
import requests
import json
import sys


API_URL = "http://localhost:8000"


def analyze_prompt(prompt: str, use_claude: bool = False):
    """
    Send a prompt to the API for analysis.
    
    Args:
        prompt: The developer prompt to analyze
        use_claude: Whether to use the Claude endpoint
    """
    endpoint = "/api/analyze-with-claude" if use_claude else "/api/analyze"
    url = f"{API_URL}{endpoint}"
    
    response = requests.post(
        url,
        json={"prompt": prompt},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def print_analysis(result):
    """Pretty print the analysis results."""
    if not result:
        return
    
    print("\n" + "="*80)
    print("SECURITY ANALYSIS RESULTS")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"   Exit Code: {result['exit_code']}")
    print(f"   Has Blockers: {'❌ YES' if result['has_blockers'] else '✅ NO'}")
    print(f"   Has Errors: {'⚠️  YES' if result['has_errors'] else '✅ NO'}")
    
    print(f"\n🔍 Findings ({len(result['devspec_findings'])}):")
    for finding in result['devspec_findings']:
        severity_icon = {
            "BLOCKER": "🚫",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }.get(finding['severity'], "•")
        
        print(f"\n   {severity_icon} [{finding['severity']}] {finding['code']}")
        print(f"      Category: {finding['category']}")
        print(f"      Message: {finding['message']}")
        print(f"      Suggestion: {finding['suggestion']}")
    
    print(f"\n💡 Guidance ({len(result['guidance'])}):")
    for item in result['guidance']:
        print(f"\n   • {item['title']}")
        print(f"     {item['detail']}")
    
    print(f"\n📝 Curated Prompt:")
    print("-" * 80)
    print(result['final_curated_prompt'])
    print("-" * 80)
    
    if result.get('claude_output'):
        print(f"\n🤖 Claude Output:")
        print("-" * 80)
        print(result['claude_output'])
        print("-" * 80)
    
    print("\n" + "="*80 + "\n")


def main():
    """Main function with example usage."""
    
    # Check if server is running
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Start it with: python api/main.py")
        sys.exit(1)
    
    print("✅ Server is running\n")
    
    # Example 1: Clean prompt (should pass)
    print("Example 1: Clean Prompt")
    print("-" * 80)
    result = analyze_prompt(
        "Create a REST API with user authentication using JWT tokens. "
        "Use HTTPS for all endpoints and store secrets in environment variables."
    )
    print_analysis(result)
    
    # Example 2: Insecure prompt (should fail)
    print("\nExample 2: Insecure Prompt")
    print("-" * 80)
    result = analyze_prompt(
        "Build an admin dashboard that auto-creates an admin user on startup. "
        "Add a /delete-user endpoint that deletes users by email without authentication. "
        "Store JWT tokens in a config.json file."
    )
    print_analysis(result)
    
    # Example 3: From file if provided
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        print(f"\nExample 3: From file '{filename}'")
        print("-" * 80)
        try:
            with open(filename, 'r') as f:
                prompt = f.read()
            result = analyze_prompt(prompt)
            print_analysis(result)
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")


if __name__ == "__main__":
    main()
