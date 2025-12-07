# 🤖 AI-Based Autonomous Gherkin Test Generator

An LLM-driven autonomous testing system that analyzes webpage HTML, identifies hoverable and popup-triggering elements, executes actions through Playwright, and generates BDD Gherkin scenarios.

## 🌟 Features

- **LLM-Powered Intelligence**: Uses OpenAI GPT-4 to analyze HTML and identify interactive elements
- **Autonomous Test Execution**: Playwright performs hover and click actions based on LLM analysis
- **No Heuristics**: Pure LLM reasoning without DOM trees, visual models, or CSS diffing
- **BDD Scenario Generation**: Automatically generates two Gherkin scenarios:
  - Hover-interaction validation (dropdowns, tooltips, navigation)
  - Popup/modal validation (dialogs, modals, overlays)

## 📋 Requirements

- Python 3.12 or higher
- OpenAI API key
- Modern web browser (Chromium will be installed by Playwright)

## 🚀 Installation

### 1. Clone or download this repository

```bash
cd ai-gherkin-generator
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install chromium
```

### 4. Set up environment variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

## 💻 Usage

### Basic Usage - Automatic Mode

The system can automatically analyze a webpage and generate test scenarios:

```bash
python src/main.py --url https://www.tivdak.com/patient-stories/
```

### Custom Test Mode

You can provide your own test steps in plain text, and the LLM will convert them to proper Gherkin format:

**Using a text file:**

```bash
python src/main.py --url https://www.tivdak.com/patient-stories/ --custom-test custom_test.txt
```

**Example custom test file (custom_test.txt):**

```
Test 1: Validate "Learn More" pop-up functionality

1. Goto the url https://www.tivdak.com/patient-stories/
2. Click the button called "Learn More"
3. A pop up will appear with the title saying "You are now leaving tivdak.com"
4. Click the cancel button
5. Click the button called "Learn More"
6. A pop up will appear with the title saying "You are now leaving tivdak.com"
7. Click the continue button
8. Verify the url has changed to "https://alishasjourney.com/"
```

The LLM will convert this into proper Gherkin:

```gherkin
Feature: Validate "Learn More" pop-up functionality

  Scenario: Verify the cancel button in the "You are now leaving tivdak.com" pop-up
    Given the user is on the "https://www.tivdak.com/patient-stories/" page
    When the user clicks the "Learn More" button
    Then a pop-up should appear with the title "You are now leaving tivdak.com"
    And the user clicks the "Cancel" button
    Then the pop-up should close

  Scenario: Verify the continue button in the pop-up redirects correctly
    Given the user is on the "https://www.tivdak.com/patient-stories/" page
    When the user clicks the "Learn More" button
    Then a pop-up should appear with the title "You are now leaving tivdak.com"
    And the user clicks the "Continue" button
    Then the page URL should change to "https://alishasjourney.com/"
```

### Advanced Options

```bash
# Run with visible browser (non-headless)
python src/main.py --url https://www.tivdak.com/patient-stories/ --headless false

# Use specific OpenAI model
python src/main.py --url https://www.tivdak.com/patient-stories/ --model gpt-4

# Custom output file
python src/main.py --url https://www.tivdak.com/patient-stories/ --output tests/my_scenarios.feature
```

### Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--url` | Yes | - | URL of the webpage to analyze |
| `--headless` | No | `true` | Run browser in headless mode (`true`/`false`) |
| `--model` | No | `gpt-4-turbo-preview` | OpenAI model to use (e.g., `gpt-4o`, `gpt-4`) |
| `--output` | No | `src/output/generated.feature` | Output file path |
| `--custom-test` | No | - | Path to custom test steps file (use `-` for stdin) |
| `--mode` | No | `auto` | Mode: `auto` for automatic analysis, `custom` for custom test conversion |

## 🔄 How It Works

### End-to-End Workflow

```
1. HTML Extraction
   ├─ Playwright loads webpage
   └─ BeautifulSoup parses HTML

2. LLM Analysis
   ├─ Identifies hover candidates (dropdowns, tooltips)
   ├─ Identifies popup candidates (modals, dialogs)
   └─ Generates action plan

3. Playwright Execution
   ├─ Executes hover actions
   ├─ Executes click actions
   └─ Captures results (visible elements, popups, URL changes)

4. LLM Interpretation
   ├─ Analyzes execution results
   └─ Identifies test-worthy interactions

5. Gherkin Generation
   ├─ Generates Scenario 1: Hover interactions
   └─ Generates Scenario 2: Popup/modal validation

6. File Output
   └─ Writes generated.feature file
```

### Architecture Principles

- **LLM performs all inference**: Element identification, selector creation, scenario logic
- **Playwright only executes**: Actions and result reporting (no interpretation)
- **BeautifulSoup only parses**: HTML extraction (no DOM tree building)
- **No heuristics**: Pure LLM reasoning, no computer vision, no CSS diffing
- **Fail-fast error handling**: Clear error messages with immediate failure

## 📁 Project Structure

```
ai-gherkin-generator/
│
├── src/
│   ├── main.py                 # Entry point with CLI
│   ├── llm_agent.py           # LLM intelligence core
│   ├── playwright_agent.py    # Action executor
│   ├── html_parser.py         # HTML extraction
│   ├── scenario_builder.py    # File writer
│   └── output/
│       └── generated.feature  # Generated scenarios
│
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables (create this)
└── README.md                # This file
```

## 📝 Example Output

The system generates a `.feature` file with two scenarios:

```gherkin
# Auto-generated Gherkin scenarios
# Generated: 2025-12-07 10:30:00

Feature: Website Interactive Elements Testing

  Scenario: Validate hover-based dropdown navigation
    Given I am on the homepage "https://www.tivdak.com/patient-stories/"
    When I hover over the element "nav .menu-item"
    Then I should see a dropdown menu appear
    And the dropdown should contain navigation links

  Scenario: Validate popup modal behavior
    Given I am on the homepage "https://www.tivdak.com/patient-stories/"
    When I click on the element "button[data-toggle='modal']"
    Then a modal popup should appear
    And the modal should have a title "Welcome"
    And the modal should contain a "Close" button
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |

### Supported OpenAI Models

- `gpt-4-turbo-preview` (default, recommended)
- `gpt-4`
- `gpt-3.5-turbo` (faster, less accurate)

## 🐛 Troubleshooting

### "OPENAI_API_KEY environment variable not set"

Make sure you've set your API key as described in the Installation section.

### "Failed to extract HTML from URL"

- Check that the URL is valid and accessible
- Verify your internet connection
- Some websites may block automated browsers

### "Selector not found or not visible"

The LLM may have identified elements that don't exist or aren't visible. This is normal for complex pages. The system will continue and note the error.

### "LLM returned invalid JSON"

Occasionally the LLM may return malformed JSON. Try running again or use a different model (GPT-4 is more reliable than GPT-3.5).

## 🔍 Testing Edge Cases

The system handles various scenarios:

- **No interactive elements found**: Generates example scenarios based on HTML structure
- **Action failures**: Logs errors and continues with remaining actions
- **Popup doesn't appear**: Notes in interpretation and adjusts scenarios
- **URL changes**: Captures navigation events in results

## 📊 Output Files

Generated `.feature` files include:

- Auto-generation timestamp
- Feature description
- Two complete Gherkin scenarios
- Given-When-Then structure
- Specific selectors and assertions

## 🤝 Contributing

This is an autonomous testing system. To extend functionality:

1. **Add new action types**: Modify `playwright_agent.py`
2. **Change LLM prompts**: Edit `llm_agent.py`
3. **Custom output formats**: Extend `scenario_builder.py`
4. **Additional validation**: Enhance `playwright_agent.py` capture methods

## 📄 License

This project is open source and available for use and modification.

## 🎯 Key Design Decisions

### Why LLM-Only Intelligence?

- **Flexibility**: Adapts to any webpage structure
- **No maintenance**: No hardcoded rules to update
- **Natural understanding**: Reasons about UI like a human tester

### Why Playwright?

- **Reliable**: Industry-standard browser automation
- **Cross-browser**: Supports Chromium, Firefox, WebKit
- **Modern**: Built for modern web applications

### Why Gherkin?

- **BDD standard**: Widely adopted in testing
- **Human-readable**: Non-technical stakeholders can understand
- **Tool support**: Works with Cucumber, Behave, etc.

## 📞 Support

For issues or questions:

1. Check the Troubleshooting section
2. Review the generated scenarios for insights
3. Verify your environment setup
4. Check OpenAI API status

---

**Built with**: Python, Playwright, OpenAI GPT-4, BeautifulSoup

**Version**: 0.1.0

