"""
AI-Based Autonomous Gherkin Test Generator
Main entry point for the application.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from html_parser import load_html
from llm_agent import LLMAgent, convert_custom_test_to_gherkin
from playwright_agent import execute_actions
from scenario_builder import write_scenarios


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║  AI-Based Autonomous Gherkin Test Generator                  ║
║  LLM-Driven Web Testing Scenario Generation                  ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def validate_environment():
    """Validate that required environment variables are set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("\nPlease set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)


def run_custom_test_mode(args, headless):
    """Run in custom test conversion mode."""
    print("🔧 MODE: Custom Test Conversion")
    print("-" * 70)
    
    # Read custom test steps
    custom_test_steps = None
    
    if args.custom_test == "-":
        # Read from stdin
        print("\n📝 Enter your test steps (press Ctrl+D or Ctrl+Z when done):\n")
        custom_test_steps = sys.stdin.read()
    elif args.custom_test:
        # Read from file
        try:
            with open(args.custom_test, 'r', encoding='utf-8') as f:
                custom_test_steps = f.read()
            print(f"\n✓ Loaded test steps from: {args.custom_test}\n")
        except FileNotFoundError:
            print(f"\n❌ ERROR: File not found: {args.custom_test}")
            sys.exit(1)
    else:
        print("\n❌ ERROR: No custom test input provided")
        print("Use --custom-test <file> or --custom-test - for stdin")
        sys.exit(1)
    
    if not custom_test_steps or not custom_test_steps.strip():
        print("\n❌ ERROR: No test steps provided")
        sys.exit(1)
    
    print("="*70)
    print("\n📋 Custom Test Steps:")
    print("-" * 70)
    print(custom_test_steps[:500])
    if len(custom_test_steps) > 500:
        print(f"\n... ({len(custom_test_steps) - 500} more characters)")
    print("-" * 70)
    
    # Convert to Gherkin
    print("\n\n🤖 Converting test steps to Gherkin format...")
    print("-" * 70)
    
    gherkin_scenarios = convert_custom_test_to_gherkin(
        custom_test_steps,
        args.url,
        model=args.model
    )
    
    print(f"✓ Conversion complete\n")
    
    # Write output file
    print("\n📝 Writing output file")
    print("-" * 70)
    
    output_path = Path(args.output)
    output_dir = str(output_path.parent)
    output_filename = output_path.name
    
    output_file = write_scenarios(
        gherkin_scenarios, 
        output_dir=output_dir,
        filename=output_filename
    )
    
    print(f"✓ Output written to: {output_file}\n")
    
    # Success summary
    print("\n" + "="*70)
    print("\n✅ SUCCESS! Custom test steps converted to Gherkin!")
    print(f"\n📄 Output file: {output_file}")
    print("\n" + "="*70 + "\n")
    
    # Display preview
    print("\n📝 Preview of generated Gherkin:\n")
    print("-" * 70)
    lines = gherkin_scenarios.split('\n')
    preview_lines = lines[:40] if len(lines) > 40 else lines
    print('\n'.join(preview_lines))
    if len(lines) > 40:
        print(f"\n... ({len(lines) - 40} more lines)")
    print("-" * 70)


def main():
    """Main execution function."""
    print_banner()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate BDD Gherkin test scenarios from webpage analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python main.py --url https://example.com
  python main.py --url https://example.com --headless false
  python main.py --url https://example.com --model gpt-4
        """
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="URL of the webpage to analyze and test"
    )
    
    parser.add_argument(
        "--headless",
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4-turbo-preview",
        help="OpenAI model to use (default: gpt-4-turbo-preview)"
    )
    
    parser.add_argument(
        "--output",
        default="src/output/generated.feature",
        help="Output file path (default: src/output/generated.feature)"
    )
    
    parser.add_argument(
        "--custom-test",
        help="Path to text file containing custom test steps, or use stdin with '-'"
    )
    
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "custom"],
        help="Mode: 'auto' for automatic analysis, 'custom' for custom test conversion (default: auto)"
    )
    
    args = parser.parse_args()
    
    # Convert headless string to boolean
    headless = args.headless.lower() == "true"
    
    # Validate environment
    validate_environment()
    
    # Determine mode based on arguments
    mode = args.mode
    if args.custom_test and mode == "auto":
        mode = "custom"
    
    print(f"\n📋 Configuration:")
    print(f"   URL: {args.url}")
    print(f"   Model: {args.model}")
    print(f"   Mode: {mode}")
    print(f"   Headless: {headless}")
    print(f"   Output: {args.output}")
    if args.custom_test:
        print(f"   Custom Test: {args.custom_test}")
    print("\n" + "="*70 + "\n")
    
    try:
        # Check if custom test mode
        if mode == "custom":
            run_custom_test_mode(args, headless)
            return
        
        # Otherwise run automatic mode
        # Step 1: Load and extract HTML
        print("STEP 1: Loading and extracting HTML")
        print("-" * 70)
        raw_html, soup = load_html(args.url, headless=headless)
        print(f"✓ HTML extraction complete\n")
        
        # Step 2: LLM analyzes HTML
        print("\nSTEP 2: Analyzing HTML with LLM")
        print("-" * 70)
        llm_agent = LLMAgent(model=args.model)
        analysis = llm_agent.analyze_html(raw_html)
        print(f"✓ HTML analysis complete\n")
        
        # Display analysis results
        print("\n📊 Analysis Results:")
        print(f"   Hover candidates: {len(analysis.get('hover_candidates', []))}")
        for i, candidate in enumerate(analysis.get('hover_candidates', [])[:3], 1):
            print(f"      {i}. {candidate.get('description')} - {candidate.get('selector')}")
        
        print(f"   Popup candidates: {len(analysis.get('popup_candidates', []))}")
        for i, candidate in enumerate(analysis.get('popup_candidates', [])[:3], 1):
            print(f"      {i}. {candidate.get('description')} - {candidate.get('selector')}")
        
        print(f"   Action plan steps: {len(analysis.get('action_plan', []))}")
        
        # Check if we have any actions to execute
        action_plan = analysis.get('action_plan', [])
        if not action_plan:
            print("\n⚠️  Warning: No actions identified in the HTML.")
            print("   Generating example scenarios based on HTML structure...\n")
        
        # Step 3: Playwright executes action plan
        print("\n\nSTEP 3: Executing action plan with Playwright")
        print("-" * 70)
        
        if action_plan:
            execution_results = execute_actions(args.url, action_plan, headless=headless)
            print(f"✓ Action execution complete\n")
            
            # Display execution summary
            print("\n🎯 Execution Summary:")
            print(f"   Actions executed: {len(execution_results.get('actions_executed', []))}")
            print(f"   Hover results: {len(execution_results.get('hover_results', []))}")
            print(f"   Popup results: {len(execution_results.get('popup_results', []))}")
            print(f"   Errors: {len(execution_results.get('errors', []))}")
            if execution_results.get('errors'):
                print("\n   ⚠️  Errors encountered:")
                for error in execution_results['errors'][:3]:
                    print(f"      - {error}")
        else:
            # No actions to execute, create minimal results
            execution_results = {
                "actions_executed": [],
                "hover_results": [],
                "popup_results": [],
                "final_url": args.url,
                "errors": []
            }
            print("   ⏭️  No actions to execute, skipping...\n")
        
        # Step 4: LLM interprets results
        print("\n\nSTEP 4: Interpreting execution results with LLM")
        print("-" * 70)
        interpretation = llm_agent.interpret_execution_results(execution_results, raw_html)
        print(f"✓ Interpretation complete\n")
        
        # Step 5: LLM generates Gherkin scenarios
        print("\n\nSTEP 5: Generating Gherkin scenarios with LLM")
        print("-" * 70)
        gherkin_scenarios = llm_agent.generate_gherkin_scenarios(
            analysis, execution_results, interpretation, args.url
        )
        print(f"✓ Gherkin generation complete\n")
        
        # Step 6: Write output file
        print("\n\nSTEP 6: Writing output file")
        print("-" * 70)
        
        # Parse output path
        output_path = Path(args.output)
        output_dir = str(output_path.parent)
        output_filename = output_path.name
        
        output_file = write_scenarios(
            gherkin_scenarios, 
            output_dir=output_dir,
            filename=output_filename
        )
        
        print(f"✓ Output written to: {output_file}\n")
        
        # Success summary
        print("\n" + "="*70)
        print("\n✅ SUCCESS! Gherkin scenarios generated successfully!")
        print(f"\n📄 Output file: {output_file}")
        print(f"📊 Scenarios generated: 2 (Hover interaction + Popup validation)")
        print("\n" + "="*70 + "\n")
        
        # Display preview of generated scenarios
        print("\n📝 Preview of generated scenarios:\n")
        print("-" * 70)
        lines = gherkin_scenarios.split('\n')
        preview_lines = lines[:30] if len(lines) > 30 else lines
        print('\n'.join(preview_lines))
        if len(lines) > 30:
            print(f"\n... ({len(lines) - 30} more lines)")
        print("-" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\n❌ ERROR: {str(e)}")
        print("\nExecution failed. Please check the error message above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

