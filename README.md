# 🤖 AI-Based Gherkin Test Generator

LLM-powered REST API that converts plain-text test steps into BDD Gherkin scenarios or auto-generates them from webpage analysis.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Create `.env` file:

```bash
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1
```

### 3. Start API Server

```bash
python src/api.py
```

Server runs at: **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

## 📡 API Endpoints

### 1. Convert Custom Test Steps to Gherkin

**POST** `/api/generate/custom`

```bash
curl -X POST http://localhost:8000/api/generate/custom \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tivdak.com/patient-
stories/",
    "test_steps": "1. Click Learn More button\n2. Verify popup appears\n3. Click Cancel",
    "model": "gpt-4.1"
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/generate/custom",
    json={
        "url": "https://www.tivdak.com/patient-
stories/",
        "test_steps": """
Test 1: Validate popup

1. Click the Learn More button
2. A popup appears with title "Leaving site"
3. Click Cancel button
4. Popup closes
        """,
        "model": "gpt-4.1"
    }
)

result = response.json()
print(result['gherkin_content'])
print(f"Saved to: {result['output_file']}")
```

### 2. Upload Custom Test File

**POST** `/api/generate/custom/file`

```bash
curl -X POST http://localhost:8000/api/generate/custom/file \
  -F "url=https://www.tivdak.com/patient-
stories/" \
  -F "test_file=@custom_test.txt" \
  -F "model=gpt-4.1"
```

### 3. Auto-Generate from Webpage Analysis

**POST** `/api/generate/auto`

```bash
curl -X POST http://localhost:8000/api/generate/auto \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tivdak.com/patient-
stories/",
    "headless": true,
    "model": "gpt-4.1"
  }'
```

### 4. List Generated Files

**GET** `/api/files`

```bash
curl http://localhost:8000/api/files
```

### 5. Download Generated File

**GET** `/api/download/{filename}`

```bash
curl http://localhost:8000/api/download/custom_generated_20251207_123456.feature -o test.feature
```

## 📝 Custom Test Format

Create a `custom_test.txt` file:

```
Test 1: Validate "Learn More" popup

1. Go to https://www.tivdak.com/patient-
stories//page
2. Click the "Learn More" button
3. A popup appears with title "You are now leaving"
4. Click the "Cancel" button
5. Verify popup closes
6. Click the "Learn More" button again
7. Click the "Continue" button
8. Verify URL changed to "https://destination.com"
```

LLM converts this to proper Gherkin:

```gherkin
Feature: Validate "Learn More" popup functionality

  Scenario: Verify cancel button closes popup
    Given the user is on "https://www.tivdak.com/patient-
stories//page"
    When the user clicks the "Learn More" button
    Then a popup should appear with title "You are now leaving"
    When the user clicks the "Cancel" button
    Then the popup should close

  Scenario: Verify continue button redirects correctly
    Given the user is on "https://www.tivdak.com/patient-
stories//page"
    When the user clicks the "Learn More" button
    Then a popup should appear with title "You are now leaving"
    When the user clicks the "Continue" button
    Then the URL should change to "https://destination.com"
```

## 🏗️ Project Structure

```
├── src/
│   ├── api.py                # FastAPI server (START HERE)
│   ├── llm_agent.py          # LLM intelligence
│   ├── playwright_agent.py   # Browser automation
│   ├── html_parser.py        # HTML extraction
│   ├── scenario_builder.py   # File writer
│   └── output/               # Generated .feature files
├── examples/
│   └── api_examples.py       # Usage examples
├── .env                      # API keys (create this)
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `OPENAI_MODEL` | No | Model to use (default: gpt-4-turbo-preview) |

## 🎯 Features

- **Custom Test Conversion**: Plain text → Gherkin scenarios
- **Auto-Generation**: Analyze webpage → Generate hover/popup tests
- **REST API**: FastAPI with Swagger docs
- **File Upload**: Support for `.txt` test files
- **Download**: Get generated `.feature` files

## 📚 API Response Format

```json
{
  "success": true,
  "message": "Gherkin scenarios generated successfully",
  "gherkin_content": "Feature: ...\n  Scenario: ...",
  "output_file": "custom_generated_20251207_123456.feature",
  "timestamp": "2025-12-07T12:34:56",
  "metadata": {
    "url": "https://www.tivdak.com/patient-
stories/",
    "mode": "custom",
    "model": "gpt-4.1"
  }
}
```

## 🛠️ Supported Models

- `gpt-4.1` (GPT-4.1, recommended)
- `gpt-4-turbo-preview` (GPT-4 Turbo)
- `gpt-4`
- `gpt-3.5-turbo`

## 📖 More Examples

See `examples/api_examples.py` for complete Python examples including:
- Health checks
- Auto-generation
- Custom test conversion
- File uploads
- Listing and downloading files

Run examples:
```bash
python examples/api_examples.py
```

## 🔧 Troubleshooting

**"OPENAI_API_KEY not set"**
- Create `.env` file with your API key

**"Failed to extract HTML"**
- Check URL is accessible
- Some sites block automation

**Connection errors**
- Make sure API server is running: `python src/api.py`
- Check http://localhost:8000/health

---

**Built with**: Python • FastAPI • OpenAI GPT-4 • Playwright • BeautifulSoup
