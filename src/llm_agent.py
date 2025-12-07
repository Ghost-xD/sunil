"""
LLM Agent Module
Core intelligence for HTML analysis, execution interpretation, and Gherkin generation.
"""

import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMAgent:
    """LLM-powered agent for autonomous test generation."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the LLM agent.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use (defaults to OPENAI_MODEL env var or gpt-4-turbo-preview)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4-turbo-preview"
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze_html(self, html: str) -> Dict[str, Any]:
        """
        Analyze HTML to identify interactive elements and create action plan.
        
        Args:
            html: Raw HTML string from the webpage
            
        Returns:
            Dictionary containing:
            {
                "hover_candidates": [{"selector": "...", "description": "..."}],
                "popup_candidates": [{"selector": "...", "description": "..."}],
                "action_plan": [
                    {"action": "hover", "selector": "...", "description": "..."},
                    {"action": "click", "selector": "...", "description": "..."}
                ]
            }
        """
        print("\nAnalyzing HTML with LLM...")
        
        # Truncate HTML if too long (GPT-4 token limits)
        max_html_length = 50000
        html_sample = html[:max_html_length]
        if len(html) > max_html_length:
            html_sample += "\n... (HTML truncated for analysis)"
        
        prompt = f"""You are an expert in web UI testing. Analyze the following HTML and identify:

1. **Hover Candidates**: Elements that likely reveal content on hover (navigation menus, dropdowns, tooltips, info icons)
2. **Popup Candidates**: Elements that likely trigger popups or modals when clicked (buttons, links with modal attributes)
3. **Action Plan**: A sequence of Playwright actions to test these interactions

For each element, provide:
- A valid CSS selector (use classes, IDs, or attributes)
- A clear description of what the element is

Create an action plan with:
- hover actions for dropdown/navigation elements
- click actions for popup triggers

Return ONLY valid JSON in this exact format:
{{
    "hover_candidates": [
        {{"selector": "nav .menu-item", "description": "Main navigation menu item"}},
        {{"selector": ".info-icon", "description": "Information tooltip trigger"}}
    ],
    "popup_candidates": [
        {{"selector": "button[data-toggle='modal']", "description": "Modal trigger button"}},
        {{"selector": ".login-link", "description": "Login popup trigger"}}
    ],
    "action_plan": [
        {{"action": "hover", "selector": "nav .menu-item", "description": "Hover over main menu to reveal dropdown"}},
        {{"action": "click", "selector": "button[data-toggle='modal']", "description": "Click to open modal popup"}}
    ]
}}

HTML to analyze:
{html_sample}

Return only the JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a web testing expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON if wrapped in markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1]) if len(lines) > 2 else result_text
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            analysis = json.loads(result_text)
            
            print(f"✓ Found {len(analysis.get('hover_candidates', []))} hover candidates")
            print(f"✓ Found {len(analysis.get('popup_candidates', []))} popup candidates")
            print(f"✓ Generated action plan with {len(analysis.get('action_plan', []))} steps")
            
            return analysis
            
        except json.JSONDecodeError as e:
            raise Exception(f"LLM returned invalid JSON: {str(e)}\nResponse: {result_text}")
        except Exception as e:
            raise Exception(f"Failed to analyze HTML: {str(e)}")
    
    def interpret_execution_results(self, results: Dict[str, Any], original_html: str) -> Dict[str, Any]:
        """
        Interpret Playwright execution results to understand what happened.
        
        Args:
            results: Execution results from Playwright agent
            original_html: Original HTML for context
            
        Returns:
            Dictionary containing interpretation of what actually happened
        """
        print("\nInterpreting execution results with LLM...")
        
        # Prepare execution summary
        execution_summary = json.dumps(results, indent=2)
        
        # Truncate HTML for context
        html_sample = original_html[:10000]
        
        prompt = f"""You are analyzing the results of automated web interactions. 

Original webpage had this HTML structure (truncated):
{html_sample}

The following actions were executed via Playwright:
{execution_summary}

Analyze these results and provide a clear interpretation:

1. **Hover Interactions**: What dropdowns/tooltips appeared? What content was revealed?
2. **Popup Interactions**: Did any popups/modals appear? What were their titles and purposes?
3. **Navigation Changes**: Did any URLs change? Where did the user navigate?
4. **Failures**: Did any actions fail? Why?
5. **Test Significance**: What would be important to validate in a test?

Return ONLY valid JSON in this format:
{{
    "hover_interactions": [
        {{"element": "...", "result": "...", "revealed_content": "...", "test_worthy": true}}
    ],
    "popup_interactions": [
        {{"element": "...", "popup_appeared": true, "popup_title": "...", "popup_purpose": "...", "test_worthy": true}}
    ],
    "navigation_changes": [
        {{"from_url": "...", "to_url": "...", "trigger": "...", "test_worthy": false}}
    ],
    "failures": [
        {{"action": "...", "selector": "...", "reason": "..."}}
    ],
    "overall_summary": "Brief summary of what happened during the test execution"
}}

Return only the JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a web testing expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON if wrapped in markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1]) if len(lines) > 2 else result_text
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            interpretation = json.loads(result_text)
            
            print(f"✓ Interpreted {len(interpretation.get('hover_interactions', []))} hover interactions")
            print(f"✓ Interpreted {len(interpretation.get('popup_interactions', []))} popup interactions")
            
            return interpretation
            
        except json.JSONDecodeError as e:
            raise Exception(f"LLM returned invalid JSON: {str(e)}\nResponse: {result_text}")
        except Exception as e:
            raise Exception(f"Failed to interpret results: {str(e)}")
    
    def generate_gherkin_scenarios(self, analysis: Dict[str, Any], results: Dict[str, Any], 
                                   interpretation: Dict[str, Any], url: str) -> str:
        """
        Generate BDD Gherkin scenarios based on analysis and execution results.
        
        Args:
            analysis: Initial HTML analysis
            results: Playwright execution results
            interpretation: LLM interpretation of results
            url: Original URL tested
            
        Returns:
            Complete .feature file content with Gherkin scenarios
        """
        print("\nGenerating Gherkin scenarios with LLM...")
        
        prompt = f"""You are a BDD testing expert. Generate Gherkin scenarios based on the following test execution.

**URL Tested**: {url}

**Initial Analysis**:
{json.dumps(analysis, indent=2)}

**Execution Results**:
{json.dumps(results, indent=2)}

**Interpretation**:
{json.dumps(interpretation, indent=2)}

Generate TWO Gherkin scenarios:

1. **Scenario 1**: Hover-based interaction validation (dropdown/navigation/tooltip)
   - Test hovering over elements and validating revealed content
   
2. **Scenario 2**: Popup/modal validation
   - Test clicking popup triggers and validating modal content

Requirements:
- Use proper Gherkin syntax (Feature, Scenario, Given, When, Then)
- Make scenarios specific and actionable
- Include actual selectors and expected content from the execution
- Make assertions meaningful (check for visible elements, text content, etc.)
- If no valid interactions were found, create realistic example scenarios

Return the complete .feature file content with both scenarios."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a BDD testing expert. Generate proper Gherkin scenarios."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2500
            )
            
            gherkin_content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if gherkin_content.startswith("```"):
                lines = gherkin_content.split("\n")
                gherkin_content = "\n".join(lines[1:-1]) if len(lines) > 2 else gherkin_content
                gherkin_content = gherkin_content.replace("```gherkin", "").replace("```", "").strip()
            
            print(f"✓ Generated Gherkin scenarios ({len(gherkin_content)} characters)")
            
            return gherkin_content
            
        except Exception as e:
            raise Exception(f"Failed to generate Gherkin scenarios: {str(e)}")
    
    def convert_custom_test_to_gherkin(self, custom_test_steps: str, url: str) -> str:
        """
        Convert user-provided plain text test steps into proper Gherkin scenarios.
        
        Args:
            custom_test_steps: Plain text test steps from user
            url: Base URL being tested
            
        Returns:
            Properly formatted Gherkin scenario
        """
        print("\nConverting custom test steps to Gherkin with LLM...")
        
        prompt = f"""You are a BDD testing expert. Convert the following plain-text test steps into a proper Gherkin scenario.

**Base URL**: {url}

**User-Provided Test Steps**:
{custom_test_steps}

**Requirements**:
1. Create a proper Gherkin Feature with a descriptive name
2. Break down the test steps into one or more Scenarios
3. Use proper Given-When-Then-And syntax
4. Be specific with element selectors (button names, text, etc.)
5. Include clear assertions (Then statements)
6. If multiple test flows are described, create separate scenarios
7. Use Background section if there are common setup steps
8. Make the scenarios executable and clear

**Example Format**:
```gherkin
Feature: [Descriptive feature name]

  Background:
    Given the user navigates to "[url]"

  Scenario: [First scenario name]
    When the user clicks the "[button name]" button
    Then a popup should appear with title "[title text]"
    And the user clicks the "[button name]" button
    Then the popup should close

  Scenario: [Second scenario name]
    When the user clicks the "[button name]" button
    Then a popup should appear with title "[title text]"
    And the user clicks the "[button name]" button
    Then the URL should change to "[expected url]"
```

Convert the test steps above into proper Gherkin format. Return ONLY the Gherkin content, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a BDD testing expert. Generate proper Gherkin scenarios from plain text test steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            gherkin_content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if gherkin_content.startswith("```"):
                lines = gherkin_content.split("\n")
                gherkin_content = "\n".join(lines[1:-1]) if len(lines) > 2 else gherkin_content
                gherkin_content = gherkin_content.replace("```gherkin", "").replace("```", "").strip()
            
            print(f"✓ Converted custom test steps to Gherkin ({len(gherkin_content)} characters)")
            
            return gherkin_content
            
        except Exception as e:
            raise Exception(f"Failed to convert custom test steps to Gherkin: {str(e)}")


# Convenience functions

def analyze_html(html: str, api_key: str = None, model: str = "gpt-4-turbo-preview") -> Dict[str, Any]:
    """Analyze HTML and return candidates and action plan."""
    agent = LLMAgent(api_key=api_key, model=model)
    return agent.analyze_html(html)


def interpret_results(results: Dict[str, Any], html: str, api_key: str = None, 
                      model: str = "gpt-4-turbo-preview") -> Dict[str, Any]:
    """Interpret execution results."""
    agent = LLMAgent(api_key=api_key, model=model)
    return agent.interpret_execution_results(results, html)


def generate_scenarios(analysis: Dict[str, Any], results: Dict[str, Any], 
                       interpretation: Dict[str, Any], url: str, api_key: str = None,
                       model: str = "gpt-4-turbo-preview") -> str:
    """Generate Gherkin scenarios."""
    agent = LLMAgent(api_key=api_key, model=model)
    return agent.generate_gherkin_scenarios(analysis, results, interpretation, url)


def convert_custom_test_to_gherkin(custom_test_steps: str, url: str, api_key: str = None,
                                   model: str = None) -> str:
    """
    Convert custom plain-text test steps into Gherkin scenarios.
    
    Args:
        custom_test_steps: Plain text test steps provided by user
        url: Base URL for the test
        api_key: OpenAI API key
        model: Model to use
        
    Returns:
        Gherkin scenario content
    """
    agent = LLMAgent(api_key=api_key, model=model)
    return agent.convert_custom_test_to_gherkin(custom_test_steps, url)

