"""
FastAPI Application for AI-Based Gherkin Test Generator
Provides REST API endpoints for test scenario generation.
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, HttpUrl
import uvicorn
from dotenv import load_dotenv

# Fix for Windows asyncio subprocess issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from html_parser import load_html
from llm_agent import LLMAgent, convert_custom_test_to_gherkin
from playwright_agent import execute_actions
from scenario_builder import write_scenarios
from cache import get_cache

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI-Based Gherkin Test Generator API",
    description="LLM-driven autonomous testing system that generates BDD Gherkin scenarios",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Ensure event loop policy is set on startup."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Request Models
class GenerateRequest(BaseModel):
    url: HttpUrl
    instructions: str
    headless: bool = True
    use_cache: bool = True
    model: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "url": "https://www.tivdak.com/patient-stories/",
                "instructions": """Test 1: Validate "Learn More" pop-up functionality

1. Go to the page
2. Click the "Learn More" button
3. A popup appears with title "You are now leaving tivdak.com"
4. Click the "Cancel" button
5. Verify popup closes
6. Click "Learn More" again
7. Click "Continue" button
8. Verify URL changes to "https://alishasjourney.com/" """,
                "headless": True,
                "model": "gpt-4.1"
            }]
        }
    }


# Response Models
class GenerationResponse(BaseModel):
    success: bool
    message: str
    gherkin_content: str
    output_file: str
    timestamp: str
    metadata: dict


# Health Check
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "AI-Based Gherkin Test Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate": "/api/generate"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key = os.getenv("OPENAI_API_KEY")
    cache_enabled = os.getenv("ENABLE_CACHE", "true").lower() in ("true", "1", "yes")
    
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key),
        "cache_enabled": cache_enabled,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    if not cache:
        return {"enabled": False, "message": "Cache is disabled"}
    
    stats = cache.stats()
    return {
        "enabled": True,
        **stats
    }


@app.post("/api/cache/clear")
async def clear_cache(expired_only: bool = False):
    """
    Clear cache entries.
    
    Args:
        expired_only: If true, only clear expired entries. If false, clear all.
    """
    cache = get_cache()
    if not cache:
        return {"success": False, "message": "Cache is disabled"}
    
    if expired_only:
        cache.clear_expired()
        return {"success": True, "message": "Cleared expired cache entries"}
    else:
        cache.clear_all()
        return {"success": True, "message": "Cleared all cache entries"}


@app.post("/api/generate", response_model=GenerationResponse)
async def generate(request: GenerateRequest):
    """
    Generate Gherkin test scenarios with browser automation.
    
    This endpoint:
    1. Loads the webpage with Playwright
    2. Uses LLM to analyze HTML and your instructions
    3. Creates an action plan based on your instructions
    4. Executes the actions in the browser (hover, click, etc.)
    5. Captures what actually happens
    6. Generates Gherkin scenarios based on real execution results
    
    Example instructions:
    - "Click the Learn More button, verify popup appears, click Cancel"
    - "Test the login flow: enter username, enter password, click submit"
    - "Hover over menu, click Products, verify product list is displayed"
    """
    try:
        url = str(request.url)
        model = request.model or os.getenv("OPENAI_MODEL") or "gpt-4-turbo-preview"
        
        print(f"\n[GENERATE] Processing request for URL: {url}")
        print(f"[GENERATE] Model: {model}, Headless: {request.headless}")
        print(f"[GENERATE] Instructions: {request.instructions[:100]}...")
        
        # Step 1: Load HTML
        print("[GENERATE] Step 1: Loading webpage HTML...")
        print(f"[GENERATE] Cache: {'Enabled' if request.use_cache else 'Disabled'}")
        
        # Temporarily disable cache if requested
        if not request.use_cache:
            import os
            old_cache_setting = os.environ.get("ENABLE_CACHE")
            os.environ["ENABLE_CACHE"] = "false"
        
        raw_html, soup = await load_html(url, headless=request.headless, use_cache=request.use_cache)
        print(f"[GENERATE] ✓ Loaded HTML ({len(raw_html)} characters)")
        
        # Restore cache setting
        if not request.use_cache and old_cache_setting:
            os.environ["ENABLE_CACHE"] = old_cache_setting
        
        # Step 2: Initialize LLM agent
        print("[GENERATE] Step 2: Initializing LLM agent...")
        llm_agent = LLMAgent(model=model)
        
        # Step 3: Execute actions intelligently (step-by-step with re-analysis)
        print("[GENERATE] Step 3: Executing actions step-by-step...")
        execution_results = await execute_actions_intelligently(
            llm_agent, url, request.instructions, request.headless
        )
        
        # Create simple analysis for Gherkin generation
        analysis = {
            "action_plan": execution_results.get("actions_executed", []),
            "hover_candidates": [],
            "popup_candidates": []
        }
        
        # Step 4: LLM interprets results
        print("[GENERATE] Step 4: Interpreting execution results...")
        interpretation = llm_agent.interpret_execution_results(execution_results, raw_html)
        print("[GENERATE] ✓ Results interpreted")
        
        # Step 5: Generate Gherkin based on actual execution
        print("[GENERATE] Step 5: Generating Gherkin scenarios from execution...")
        gherkin_content = llm_agent.generate_gherkin_scenarios(
            analysis, execution_results, interpretation, url
        )
        
        # Write Output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.feature"
        output_file = write_scenarios(gherkin_content, filename=filename)
        
        print(f"[GENERATE] ✓ Complete! Generated: {output_file}")
        
        return GenerationResponse(
            success=True,
            message="Gherkin scenarios generated successfully from browser execution",
            gherkin_content=gherkin_content,
            output_file=filename,
            timestamp=datetime.now().isoformat(),
            metadata={
                "url": url,
                "model": model,
                "headless": request.headless,
                "instructions_length": len(request.instructions),
                "actions_executed": len(execution_results.get('actions_executed', [])),
                "errors": len(execution_results.get('errors', []))
            }
        )
        
    except Exception as e:
        print(f"[GENERATE] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_click_action(page, selector: str, step_description: str, use_text_locator: bool = False) -> bool:
    """
    Robust click execution with multiple fallback strategies.
    Special handling for popup/modal buttons.
    Supports both CSS selectors and Playwright text locators.
    """
    print(f"Clicking: {selector}")
    
    # Detect if we're clicking inside a popup/modal
    is_popup_button = any(keyword in step_description.lower() for keyword in 
                          ['popup', 'modal', 'dialog', 'cancel', 'close', 'continue', 'confirm', 'ok'])
    
    # Detect invalid selectors with :contains() and convert to text locator
    if ':contains(' in selector or ':has-text(' in selector:
        print(f"⚠ Detected invalid selector with :contains(), converting to text locator")
        # Extract text from selector like "button:contains('Learn More')" -> "Learn More"
        import re
        match = re.search(r":contains\(['\"]([^'\"]+)['\"]\)", selector)
        if match:
            text = match.group(1)
            selector = text
            use_text_locator = True
            print(f"→ Using text locator: '{text}'")
        else:
            # Try :has-text() format
            match = re.search(r":has-text\(['\"]([^'\"]+)['\"]\)", selector)
            if match:
                text = match.group(1)
                selector = text
                use_text_locator = True
                print(f"→ Using text locator: '{text}'")
    
    strategies = [
        {
            "name": "Standard click (visible)", 
            "fn": lambda elem: elem.click(timeout=5000),
            "require_visible": True
        },
        {
            "name": "Force click (visible)", 
            "fn": lambda elem: elem.click(force=True, timeout=5000),
            "require_visible": True
        },
        {
            "name": "JS click (bypass visibility)", 
            "fn": lambda elem: elem.evaluate("el => el.click()"),
            "require_visible": False
        },
        {
            "name": "Dispatch click (bypass visibility)", 
            "fn": lambda elem: elem.dispatch_event("click"),
            "require_visible": False
        },
    ]
    
    for strategy in strategies:
        try:
            print(f"Trying: {strategy['name']}")
            
            # For popup buttons, wait longer for animations to complete
            if is_popup_button:
                await page.wait_for_timeout(1000)  # Extra wait for popup animation
            
            # Use text locator if specified, otherwise use CSS selector
            if use_text_locator:
                # For popup buttons, scope to popup for better reliability
                if is_popup_button:
                    # Try to find popup first, then scope text search to it
                    popup_found = False
                    modal_selectors = [
                        "[role='dialog']:visible",
                        "[aria-modal='true']:visible",
                        ".modal:visible",
                        ".popup:visible"
                    ]
                    for modal_selector in modal_selectors:
                        try:
                            modal = page.locator(modal_selector).first
                            if await modal.is_visible():
                                # Scope text search to popup
                                all_elements = modal.get_by_text(selector, exact=False)
                                popup_found = True
                                print(f"✓ Scoped text search to popup: {modal_selector}")
                                break
                        except:
                            continue
                    
                    if not popup_found:
                        # Fallback to page-wide search
                        all_elements = page.get_by_text(selector, exact=False)
                else:
                    # Use Playwright's get_by_text for text-based matching
                    # This works for buttons, links, and any clickable element with that text
                    all_elements = page.get_by_text(selector, exact=False)
            else:
                # Use standard CSS selector
                all_elements = page.locator(selector)
            
            element_count = await all_elements.count()
            
            if element_count > 1:
                print(f"Found {element_count} elements, looking for visible one...")
                # Try to find a visible element
                element = None
                for i in range(element_count):
                    try:
                        candidate = all_elements.nth(i)
                        if await candidate.is_visible():
                            element = candidate
                            print(f"Using visible element #{i}")
                            break
                    except:
                        continue
                
                # If no visible element, use first one
                if not element:
                    element = all_elements.first
            else:
                element = all_elements.first
            
            # Wait for element to exist (attached to DOM)
            await element.wait_for(state="attached", timeout=3000)
            
            # Only wait for visibility if required by strategy
            if strategy.get("require_visible", True):
                try:
                    await element.wait_for(state="visible", timeout=3000)
                    await element.scroll_into_view_if_needed()
                except:
                    # If not visible, this strategy won't work, try next
                    print(f"Element not visible, skipping this strategy")
                    continue
                await page.wait_for_timeout(300)
            else:
                # For JS/dispatch clicks, just wait a bit
                await page.wait_for_timeout(500)
            
            # Execute the strategy
            await strategy['fn'](element)
            
            print(f"✓ {strategy['name']} successful")
            
            # Wait for page to respond
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass  # Timeout is ok
            await page.wait_for_timeout(2000)
            
            # Check if modal closed or navigation happened
            if is_popup_button:
                try:
                    # Wait for any modals to close after clicking popup button
                    await page.locator("[role='dialog']:visible, .modal:visible, [aria-modal='true']:visible").wait_for(state="hidden", timeout=5000)
                    print(f"✓ Modal closed after click")
                    # Extra wait to ensure popup is fully gone and DOM is stable
                    await page.wait_for_timeout(1000)
                except:
                    # Popup might have closed immediately or wasn't visible
                    # Still wait to ensure DOM is stable
                    await page.wait_for_timeout(1000)
            
            return True
            
        except Exception as e:
            print(f"{strategy['name']} failed: {str(e)}")
            continue
    
    print(f"✗ All click strategies failed for: {selector}")
    return False


async def extract_popup_html(page, use_cache: bool = True) -> str:
    modal_selectors = [
        "[role='dialog']:visible",
        "[aria-modal='true']:visible",
        ".modal:visible",
        ".modal.show:visible",
        ".popup:visible",
        ".modal-dialog:visible",
        "[class*='modal']:visible",
        "[class*='popup']:visible",
        "[class*='dialog']:visible"
    ]
    
    for modal_selector in modal_selectors:
        try:
            modal = page.locator(modal_selector).first
            if await modal.is_visible():
                popup_html = await modal.inner_html()
                if use_cache:
                    cache = get_cache()
                    if cache:
                        structure_key = normalize_popup_html_for_cache(popup_html)
                        cached_html = cache.get_popup_html(structure_key)
                        if cached_html:
                            print(f"✓ Using cached popup HTML ({len(cached_html)} chars)")
                            return cached_html
                        cache.set_popup_html(structure_key, popup_html)
                print(f"✓ Extracted popup HTML ({len(popup_html)} chars) using selector: {modal_selector}")
                return popup_html
        except:
            continue
    return ""


async def is_popup_visible(page) -> bool:
    """
    Check if any popup/modal is currently visible on the page.
    """
    modal_selectors = [
        "[role='dialog']:visible",
        "[aria-modal='true']:visible",
        ".modal:visible",
        ".popup:visible"
    ]
    
    for modal_selector in modal_selectors:
        try:
            modal = page.locator(modal_selector).first
            if await modal.is_visible():
                return True
        except:
            continue
    
    return False


async def execute_hover_action(page, selector: str, step_description: str) -> bool:
    """
    Robust hover execution.
    """
    print(f"Hovering: {selector}")
    
    try:
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=5000)
        await element.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        await element.hover()
        await page.wait_for_timeout(1500)  # Wait for hover effects
        print(f"✓ Hover successful")
        return True
        
    except Exception as e:
        print(f"✗ Hover failed: {str(e)}")
        return False


async def execute_actions_intelligently(
    llm_agent: LLMAgent,
    url: str,
    instructions: str,
    headless: bool
) -> dict:
    """
    Execute actions intelligently - one step at a time with page re-analysis.
    """
    from playwright.async_api import async_playwright
    
    all_results = {
        "actions_executed": [],
        "hover_results": [],
        "popup_results": [],
        "final_url": url,
        "errors": []
    }
    
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            print(f"Opening URL: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            # Parse instructions into steps (remove numbers, clean up)
            steps = []
            for line in instructions.split('\n'):
                line = line.strip()
                if not line or not any(c.isalpha() for c in line):
                    continue
                # Remove leading numbers like "1.", "2)", etc.
                import re
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                if line:
                    steps.append(line)
            
            # Track last action to detect redundant popup button clicks
            last_action = None
            
            for i, step in enumerate(steps, 1):
                print(f"\n{'='*70}")
                print(f"Step {i}/{len(steps)}: {step}")
                print(f"Current URL: {page.url}")
                print(f"{'='*70}")
                
                # Detect if this step is popup-related
                is_popup_step = any(keyword in step.lower() for keyword in 
                                   ['popup', 'modal', 'dialog', 'cancel', 'close', 'continue', 'confirm', 'ok'])
                
                # Check if this is a popup button click step (Cancel, Close, Continue, etc.)
                is_popup_button_step = any(keyword in step.lower() for keyword in 
                                          ['cancel', 'close', 'continue', 'confirm', 'ok', 'dismiss'])
                
                # Check if this is an observation step (popup appears, popup closes, etc.)
                is_observation_step = any(phrase in step.lower() for phrase in 
                                        ['popup appears', 'modal appears', 'dialog appears', 
                                         'popup closes', 'modal closes', 'dialog closes',
                                         'popup is visible', 'modal is visible', 'dialog is visible',
                                         'verify popup', 'check popup', 'popup should'])
                
                # If it's clearly an observation step, skip LLM call and mark as observation
                if is_observation_step and not any(action_word in step.lower() for action_word in ['click', 'press', 'tap', 'select']):
                    print(f"ℹ Observation step detected - no action needed")
                    all_results["actions_executed"].append({
                        "step": step,
                        "action": "observation",
                        "success": True,
                        "note": "Observation/verification step - no action required"
                    })
                    continue
                
                # If it's a popup button step, check if popup exists BEFORE extracting HTML
                if is_popup_button_step:
                    popup_visible = await is_popup_visible(page)
                    if not popup_visible:
                        print(f"ℹ Popup not visible - step likely already completed or popup was closed")
                        print(f"ℹ Skipping step: {step}")
                        all_results["actions_executed"].append({
                            "step": step,
                            "action": "skip",
                            "success": True,
                            "note": "Popup not visible - already closed or step completed"
                        })
                        continue
                
                # Get HTML - only popup HTML if it's a popup step
                try:
                    if is_popup_step and not is_observation_step:
                        # For popup steps that are NOT observations, try to extract popup HTML
                        # But first check if popup is visible (for button steps we already checked above)
                        if is_popup_button_step:
                            # We already verified popup is visible above, so extract it (with cache)
                            popup_html = await extract_popup_html(page, use_cache=True)
                            if popup_html:
                                current_html = popup_html
                                print(f"✓ Using popup-only HTML ({len(current_html)} chars) - optimized for rate limits")
                            else:
                                # Popup disappeared between check and extraction
                                print(f"ℹ Popup disappeared - step likely already completed")
                                print(f"ℹ Skipping step: {step}")
                                all_results["actions_executed"].append({
                                    "step": step,
                                    "action": "skip",
                                    "success": True,
                                    "note": "Popup disappeared - already closed"
                                })
                                continue
                        else:
                            # Non-button popup step - try to extract popup HTML (with cache)
                            popup_html = await extract_popup_html(page, use_cache=True)
                            if popup_html:
                                current_html = popup_html
                                print(f"✓ Using popup-only HTML ({len(current_html)} chars) - optimized for rate limits")
                            else:
                                # Fallback to full page if popup not found
                                current_html = await page.content()
                                print(f"⚠ Popup not found, using full page HTML ({len(current_html)} chars)")
                    elif is_observation_step:
                        # For observation steps, use minimal HTML or just check popup visibility
                        current_html = await page.content()
                        # Truncate heavily for observation steps since we just need to verify
                        current_html = current_html[:5000]  # Very small for observations
                        print(f"ℹ Observation step - using minimal HTML ({len(current_html)} chars)")
                    else:
                        # Regular step - use full page HTML
                        current_html = await page.content()
                        print(f"Captured HTML ({len(current_html)} chars)")
                except Exception as e:
                    print(f"✗ Failed to get page content: {str(e)}")
                    all_results["errors"].append(f"Step {i}: Failed to get page content")
                    continue
                
                # Ask LLM what to do for this specific step
                action = await get_single_action_from_step(llm_agent, current_html, step, url, is_popup_step=is_popup_step)
                
                if not action:
                    print(f"ℹ No action needed (verification/wait step)")
                    all_results["actions_executed"].append({
                        "step": step,
                        "action": "none",
                        "success": True,
                        "note": "Observation/verification step"
                    })
                    continue
                
                # Execute the action with robust error handling
                try:
                    if action['action'] == 'click':
                        use_text_locator = action.get('use_text_locator', False)
                        success = await execute_click_action(page, action['selector'], step, use_text_locator=use_text_locator)
                        
                        # Track last action for detecting redundant clicks
                        last_action = {
                            "action": "click",
                            "selector": action['selector'],
                            "is_popup_button": is_popup_button_step,
                            "step": step
                        }
                        
                        all_results["actions_executed"].append({
                            "step": step,
                            "action": "click",
                            "selector": action['selector'],
                            "use_text_locator": use_text_locator,
                            "success": success
                        })
                        
                    elif action['action'] == 'hover':
                        success = await execute_hover_action(page, action['selector'], step)
                        all_results["actions_executed"].append({
                            "step": step,
                            "action": "hover",
                            "selector": action['selector'],
                            "success": success
                        })
                    
                except Exception as e:
                    error_msg = f"Failed to execute {action.get('action', 'unknown')} on {action.get('selector', 'unknown')}: {str(e)}"
                    print(f"✗ {error_msg}")
                    all_results["errors"].append(error_msg)
                    all_results["actions_executed"].append({
                        "step": step,
                        "action": action.get('action'),
                        "selector": action.get('selector'),
                        "success": False,
                        "error": str(e)
                    })
                    
                    # Stop execution on any action failure - no point continuing
                    print(f"\n{'='*70}")
                    print(f"✗ CRITICAL FAILURE on step {i}/{len(steps)}")
                    print(f"✗ Action failed: {error_msg}")
                    print(f"✗ Stopping execution - cannot continue reliably")
                    print(f"{'='*70}\n")
                    all_results["errors"].append(f"STOPPED at step {i}: {error_msg}")
                    break  # Stop execution immediately
            
            all_results["final_url"] = page.url
            
            # Print summary
            print(f"\n{'='*70}")
            print(f"✓ EXECUTION COMPLETE")
            print(f"{'='*70}")
            print(f"Total Steps: {len(steps)}")
            print(f"Actions Executed: {len(all_results['actions_executed'])}")
            print(f"Successful: {sum(1 for a in all_results['actions_executed'] if a.get('success'))}")
            print(f"Failed: {sum(1 for a in all_results['actions_executed'] if not a.get('success'))}")
            print(f"Errors: {len(all_results['errors'])}")
            print(f"Final URL: {page.url}")
            print(f"{'='*70}\n")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        all_results["errors"].append(f"Fatal error: {str(e)}")
        print(f"✗ Fatal error: {str(e)}")
    
    return all_results


def normalize_popup_html_for_cache(html: str) -> str:
    """
    Normalize popup HTML for caching by extracting essential structure.
    Removes dynamic attributes and focuses on button text and structure.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract all buttons and their text
        buttons = []
        for button in soup.find_all(['button', 'a', 'input']):
            text = button.get_text(strip=True)
            if text:
                # Get element type
                tag = button.name
                # Get essential attributes (not dynamic ones)
                attrs = {}
                for attr in ['type', 'role']:
                    if button.get(attr):
                        attrs[attr] = button.get(attr)
                
                buttons.append({
                    'tag': tag,
                    'text': text,
                    'attrs': attrs
                })
        
        # Create normalized structure
        normalized = {
            'buttons': sorted(buttons, key=lambda x: x['text']),
            'html_length': len(html)
        }
        
        import json
        return json.dumps(normalized, sort_keys=True)
    except:
        # Fallback: use a hash of the HTML length and first 1000 chars
        return f"{len(html)}:{hash(html[:1000])}"


async def get_single_action_from_step(
    llm_agent: LLMAgent,
    current_html: str,
    step: str,
    url: str,
    is_popup_step: bool = False
) -> dict:
    """
    Ask LLM to create ONE action for ONE step based on current page HTML.
    If is_popup_step is True, uses popup-optimized prompt and smaller HTML.
    """
    normalized_structure = None
    if is_popup_step:
        normalized_structure = normalize_popup_html_for_cache(current_html) if current_html else None
        html_sample = current_html[:5000] if current_html else ""
        if len(current_html) > 5000:
            html_sample += "\n... (truncated)"
        context_note = "**NOTE: This is POPUP/MODAL HTML only - analyze only elements within this popup.**"
    else:
        max_length = 80000
        html_sample = current_html[:max_length]
        if len(current_html) > max_length:
            html_sample += "\n... (truncated)"
        context_note = ""
    
    # Build popup-specific instructions if this is a popup step
    popup_instructions = ""
    if is_popup_step:
        popup_instructions = """
**CRITICAL FOR POPUP STEPS:**
- This HTML contains ONLY the popup/modal content
- ALWAYS use text-based selector (use_text_locator: true) for popup buttons
- Do NOT use aria-label - use only visible text
- Popup buttons are dynamically generated - text is most reliable
- Example: "Click Cancel" → {{"selector": "Cancel", "use_text_locator": true}}
- Example: "Click Continue" → {{"selector": "Continue", "use_text_locator": true}}
"""
    
    prompt = f"""You must find the EXACT element from the HTML provided.

**Test Step**: {step}
{context_note}
{popup_instructions}

**ACTUAL HTML from page**:
{html_sample}

TASK: Determine if action needed, find element, return selector.

ACTION KEYWORDS:
- "click", "press", "tap", "select", "choose", "submit" → action="click"
- "hover", "mouseover" → action="hover"
- "wait", "verify", "check", "should", "expect", "assert", "appears", "closes", "is visible" → action=null

CRITICAL: Observation steps return action=null:
- "A popup appears" → action=null (just observing, no action needed)
- "Popup closes" → action=null (just observing, no action needed)
- "Verify popup is visible" → action=null (verification step)
- "Click Cancel" → action="click" (this IS an action)

ELEMENT FINDING STRATEGY:
1. Extract target keyword from step
   Examples: "Click Learn More" → "Learn More"
             "Click Submit button" → "Submit"
             "Click the Continue link" → "Continue"
             "Press Login" → "Login"

2. IMPORTANT: The target can be ANY clickable element (button, link, div, span, etc.)
   - "Learn More" might be: <button>Learn More</button>, <a>Learn More</a>, <div class="learn-more">Learn More</div>
   - Look for ALL clickable elements, not just buttons!

3. IMPORTANT FOR POPUPS: If step mentions "popup", "modal", "dialog", "cancel", "close", "continue", "confirm", "ok":
   - ALWAYS use text-based selector (use_text_locator: true)
   - Popup buttons are often dynamically generated and text is most reliable
   - Do NOT check aria-label - use only visible text
   - Example: "Click Cancel in popup" → selector: "Cancel", use_text_locator: true

4. Search HTML for matching elements in this priority (SKIP aria-label):
   a) ID containing keyword: <button id="learn-more-btn"> → #learn-more-btn
      <a id="learn-more-link"> → #learn-more-link
   b) Class containing keyword: <button class="btn-learn-more"> → button.btn-learn-more
      <a class="learn-more-link"> → a.learn-more-link
      <div class="learn-more"> → div.learn-more
   c) Name attribute: <input name="learn-more"> → input[name="learn-more"]
   d) Value attribute: <input value="Learn More"> → input[value="Learn More"]
   e) Href containing keyword: <a href="/learn-more"> → a[href*="learn-more"]
   f) Data attributes: <button data-action="learn-more"> → button[data-action="learn-more"]
   
5. If element has text content but no unique id/class:
   - For popup elements: ALWAYS use text locator (use_text_locator: true)
   - For regular elements: Look for parent container with id/class
   - ONLY use CSS selector if you can find a unique, reliable one
   - When in doubt, prefer text locator for popups

6. CRITICAL SELECTOR RULES:
   - For POPUPS: Prefer text locators (use_text_locator: true) - they're more reliable
   - For regular elements: PREFER CSS selectors: #id, .class, tag[attribute], tag[attribute*="value"]
   - CSS selectors MUST work with document.querySelector()
   - NEVER use :contains(), :has-text(), text=, or jQuery syntax in CSS selectors
   - Text locator format:
     * Set "use_text_locator": true
     * Set "selector" to just the text string (e.g., "Cancel", "Continue", "Learn More")
     * This works for ANY clickable element (button, link, div, span, etc.)
   
EXAMPLES - RIGHT vs WRONG:

For "Click Cancel in popup":
WRONG: button:contains('Cancel')  ← Invalid CSS!
WRONG: selector: "button[aria-label*='Cancel']", use_text_locator: false  ← Don't use aria-label!
RIGHT: selector: "Cancel", use_text_locator: true  ← Text locator for popups (PREFERRED)

For "Click Continue button in modal":
WRONG: :has-text('Continue')  ← Invalid CSS!
RIGHT: selector: "Continue", use_text_locator: true  ← Text locator for popups (PREFERRED)

For "Click Learn More" (regular page element):
WRONG: button:contains('Learn More')  ← Invalid CSS!
RIGHT: selector: "a.btn-primary[href*='learn']", use_text_locator: false  ← CSS selector if available
RIGHT: selector: "Learn More", use_text_locator: true  ← Text locator if no CSS selector

RETURN JSON:
{{
    "action": "click",
    "selector": "#actual-id-from-html",
    "use_text_locator": false,
    "reasoning": "Found <button id='actual-id-from-html'>Learn More</button> in HTML"
}}

OR if only text is available:
{{
    "action": "click",
    "selector": "Learn More",
    "use_text_locator": true,
    "reasoning": "Found <a>Learn More</a> with no unique id/class, using text locator"
}}

If no action: {{"action": null}}

VERIFY: Your selector MUST work with document.querySelector() OR be a text string for Playwright text locator!

Return ONLY JSON."""

    cache_key_prompt = prompt
    if is_popup_step:
        popup_state = "visible" if normalized_structure else "hidden"
        import re
        button_match = re.search(r'(?:click|press|tap|select)\s+(?:the\s+)?(cancel|close|continue|confirm|ok|dismiss|learn\s+more|submit|yes|no)', step.lower())
        button_name = button_match.group(1) if button_match else "unknown"
        cache_key_prompt = f"popup:{popup_state}||button:{button_name}||structure:{normalized_structure if normalized_structure else 'none'}"
    
    cache = get_cache()
    if cache:
        cache_prompt = cache_key_prompt if is_popup_step else prompt
        cached_response = cache.get_llm_response(cache_prompt, llm_agent.model)
        if cached_response:
            result_text = cached_response
        else:
            response = llm_agent.client.chat.completions.create(
                model=llm_agent.model,
                messages=[
                    {"role": "system", "content": "You are a Playwright expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            result_text = response.choices[0].message.content.strip()
            cache.set_llm_response(cache_prompt, result_text, llm_agent.model)
    else:
        # No cache, call LLM directly
        response = llm_agent.client.chat.completions.create(
            model=llm_agent.model,
            messages=[
                {"role": "system", "content": "You are a Playwright expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        result_text = response.choices[0].message.content.strip()
    
    try:
        
        # Clean JSON
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1]) if len(lines) > 2 else result_text
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        action_data = json.loads(result_text)
        
        if action_data.get("action"):
            print(f"[LLM] Action: {action_data['action']} on {action_data['selector']}")
            print(f"[LLM] Reasoning: {action_data.get('reasoning', 'N/A')}")
            return action_data
        else:
            return None
            
    except Exception as e:
        print(f"[LLM] Error getting action: {str(e)}")
        return None




# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("\nPlease set your OpenAI API key in .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("🚀 Starting AI-Based Gherkin Test Generator API Server")
    print("="*70)
    print(f"\n📋 Configuration:")
    print(f"   OpenAI API Key: {'✓ Configured' if api_key else '✗ Not set'}")
    print(f"   Default Model: {os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')}")
    print(f"\n🌐 Server will start at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"📖 Alternative docs: http://localhost:8000/redoc")
    print("\n" + "="*70 + "\n")
    
    # Note: reload=False on Windows to avoid event loop issues with Playwright
    # For development, manually restart the server after code changes
    uvicorn.run(
        app,  # Pass app directly instead of string when reload=False
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled on Windows for Playwright compatibility
        log_level="info"
    )

