# 🤖 AI-Based Gherkin Test Generator

LLM-powered REST API that converts your plain-text test instructions into BDD Gherkin scenarios.

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

## 📡 API Usage

### Generate Gherkin from Your Instructions

**POST** `/api/generate`

Simply describe what you want to test in plain English, and the LLM converts it to proper Gherkin format.

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tivdak.com/patient-stories/",
    "instructions": "1. Click the Learn More button\n2. A popup appears with title \"You are now leaving tivdak.com\"\n3. Click Cancel button\n4. Popup closes\n5. Click Learn More again\n6. Click Continue button\n7. Verify URL changes to https://alishasjourney.com/",
    "headless": true,
    "model": "gpt-4.1"
  }'
```

### Other Endpoints

**Health Check** - `GET /health`
```bash
curl http://localhost:8000/health
```

**Cache Stats** - `GET /api/cache/stats`
```bash
curl http://localhost:8000/api/cache/stats
```

**Clear Cache** - `POST /api/cache/clear`
```bash
# Clear all cache
curl -X POST http://localhost:8000/api/cache/clear

# Clear only expired
curl -X POST "http://localhost:8000/api/cache/clear?expired_only=true"
```

## 📝 How to Write Instructions

The system is **intelligent and works with ANY website**. Just describe what you want to test in plain English.

### Instruction Format

**Simple (Recommended):**
```
Click Login
Enter username
Enter password
Click Submit
Verify dashboard appears
```

**Numbered:**
```
1. Click the Learn More button
2. Click Cancel in popup
3. Click Learn More again
4. Click Continue
5. Verify URL changed
```

**Descriptive:**
```
Click on the Learn More link
Wait for popup to appear
Click the Cancel button
Check that popup closes
Click Learn More button
Click Continue button
```

### Real Examples

**E-commerce Site:**
```
Hover over Products menu
Click Laptops category
Click first product
Click Add to Cart
Click Checkout button
```

**Login Flow:**
```
Click Sign In
Enter test@example.com
Enter password123
Click Login button
Verify Welcome message
```

**Modal/Popup:**
```
Click Open Dialog
Click Cancel button
Click Open Dialog again
Click Confirm button
```

### Key Points

✅ **Works on ANY website** - System analyzes actual HTML  
✅ **Finds elements intelligently** - Matches keywords to IDs, classes, text  
✅ **Multiple click strategies** - Force click, JS click, dispatch events  
✅ **Handles modals/popups** - Waits for them to open/close  
✅ **Continues on errors** - Doesn't stop if one step fails  
✅ **Detailed logging** - See exactly what's happening

The LLM will convert any of these formats into proper Gherkin:

```gherkin
Feature: User login validation

  Scenario: Successful login with valid credentials
    Given the user is on "https://example.com"
    When the user enters "john@example.com" in the email field
    And the user enters "password123" in the password field
    And the user clicks the "Login" button
    Then the dashboard page should load
```

## 📖 Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | The URL of the page to test |
| `instructions` | string | Yes | - | Your test instructions in plain text |
| `headless` | boolean | No | `true` | Run browser in headless mode (`false` to see browser) |
| `model` | string | No | `gpt-4-turbo-preview` | OpenAI model to use |

## 📖 API Response

```json
{
  "success": true,
  "message": "Gherkin scenarios generated successfully from your instructions",
  "gherkin_content": "Feature: ...\n  Scenario: ...",
  "output_file": "generated_20251207_123456.feature",
  "timestamp": "2025-12-07T12:34:56",
  "metadata": {
    "url": "https://example.com",
    "model": "gpt-4.1",
    "instructions_length": 245
  }
}
```

## 📁 Generated Files

All generated `.feature` files are saved in `src/output/` directory.

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4-turbo-preview` | Model to use |
| `ENABLE_CACHE` | No | `true` | Enable HTML/LLM caching (saves tokens!) |
| `CACHE_TTL_HOURS` | No | `24` | Cache expiration time in hours |

**Recommended Model:**
- `gpt-4.1` (GPT-4.1, fastest and most capable - recommended)

## 💾 Caching (Save Tokens During Development!)

The system automatically caches:
- ✅ **HTML content** from URLs (avoids re-loading pages)
- ✅ **LLM responses** (same prompt = reuse response)

**Benefits:**
- 🚀 Faster development (instant responses from cache)
- 💰 Save OpenAI tokens (no duplicate API calls)
- 🔄 Consistent results during testing

**Cache Management Endpoints:**

```bash
# View cache statistics
curl http://localhost:8000/api/cache/stats

# Clear all cache
curl -X POST http://localhost:8000/api/cache/clear

# Clear only expired entries
curl -X POST http://localhost:8000/api/cache/clear?expired_only=true
```

**Disable Cache:**
Set in `.env`: `ENABLE_CACHE=false`

## 🏗️ Project Structure

```
├── src/
│   ├── api.py                # FastAPI server (START HERE)
│   ├── llm_agent.py          # LLM intelligence
│   ├── playwright_agent.py   # Browser automation
│   ├── html_parser.py        # HTML extraction
│   ├── scenario_builder.py   # File writer
│   ├── cache.py              # SQLite caching (saves tokens)
│   ├── .cache/               # Cache database (auto-created)
│   └── output/               # Generated .feature files
├── examples/
│   └── api_examples.py       # Usage examples
├── .env                      # API keys (create this)
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🛠️ Troubleshooting

**"OPENAI_API_KEY not set"**
- Create `.env` file with your API key

**Connection errors**
- Make sure API server is running: `python src/api.py`
- Check http://localhost:8000/health

**"Invalid JSON" errors**
- Occasionally the LLM returns malformed JSON
- Try running the request again
- GPT-4.1 is more reliable than GPT-3.5

## 💡 Tips

1. **Be specific**: The more detail in your instructions, the better the Gherkin output
2. **Use numbered steps**: Makes it easier for the LLM to understand sequence
3. **Include expected results**: Use "Verify", "Should see", "Expect" for assertions
4. **Break complex flows**: Split long tests into multiple smaller scenarios

## 📚 More Examples

See `examples/api_examples.py` for complete Python code examples.

Run examples:
```bash
python examples/api_examples.py
```

---

**Built with**: Python • FastAPI • OpenAI GPT-4 • Playwright • BeautifulSoup
