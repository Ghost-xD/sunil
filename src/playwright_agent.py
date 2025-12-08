"""
Playwright Agent Module
Executes action plans and captures results without interpretation.
"""

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Any
import asyncio


class PlaywrightAgent:
    """Executes Playwright actions and reports results."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the Playwright agent.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def start_browser(self, url: str):
        """Start browser and navigate to URL."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        print(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)  # Wait for initial load
    
    async def close_browser(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def execute_action_plan(self, url: str, action_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a list of actions from the LLM.
        
        Args:
            url: The URL to navigate to
            action_plan: List of actions with format:
                [{"action": "hover", "selector": "...", "description": "..."}]
        
        Returns:
            Dictionary containing execution results:
            {
                "actions_executed": [...],
                "hover_results": [...],
                "popup_results": [...],
                "final_url": "...",
                "errors": [...]
            }
        """
        results = {
            "actions_executed": [],
            "hover_results": [],
            "popup_results": [],
            "final_url": "",
            "errors": []
        }
        
        try:
            await self.start_browser(url)
            
            for action_item in action_plan:
                action = action_item.get("action")
                selector = action_item.get("selector")
                description = action_item.get("description", "")
                
                print(f"\nExecuting: {action} on '{selector}' - {description}")
                
                action_result = {
                    "action": action,
                    "selector": selector,
                    "description": description,
                    "success": False,
                    "details": {}
                }
                
                try:
                    if action == "hover":
                        result = await self._execute_hover(selector)
                        action_result["success"] = result["success"]
                        action_result["details"] = result
                        if result["success"]:
                            results["hover_results"].append(result)
                    
                    elif action == "click":
                        result = await self._execute_click(selector)
                        action_result["success"] = result["success"]
                        action_result["details"] = result
                        if result.get("popup_detected"):
                            results["popup_results"].append(result)
                    
                    else:
                        action_result["details"]["error"] = f"Unknown action: {action}"
                        results["errors"].append(f"Unknown action: {action}")
                
                except Exception as e:
                    action_result["details"]["error"] = str(e)
                    results["errors"].append(f"Error executing {action} on {selector}: {str(e)}")
                    print(f"Error: {str(e)}")
                
                results["actions_executed"].append(action_result)
            
            # Capture final URL
            results["final_url"] = self.page.url
            
        except Exception as e:
            results["errors"].append(f"Fatal error during execution: {str(e)}")
            print(f"Fatal error: {str(e)}")
        
        finally:
            await self.close_browser()
        
        return results
    
    async def _execute_hover(self, selector: str) -> Dict[str, Any]:
        """
        Execute hover action and capture what appears.
        
        Args:
            selector: CSS selector to hover over
            
        Returns:
            Dictionary with hover results
        """
        result = {
            "action": "hover",
            "selector": selector,
            "success": False,
            "newly_visible_elements": [],
            "element_count_before": 0,
            "element_count_after": 0
        }
        
        try:
            # Get visible elements count before hover
            visible_before = await self.page.locator("*:visible").count()
            result["element_count_before"] = visible_before
            
            # Wait for element and hover with retry
            element = await self._wait_for_element_with_retry(selector, timeout=10000)
            await element.hover()
            
            # Wait for any animations
            await self.page.wait_for_timeout(1000)
            
            # Get visible elements count after hover
            visible_after = await self.page.locator("*:visible").count()
            result["element_count_after"] = visible_after
            
            # Try to capture newly visible elements (dropdowns, tooltips, etc.)
            # Look for common dropdown/tooltip patterns
            dropdown_selectors = [
                f"{selector} + ul",
                f"{selector} + div[role='menu']",
                f"{selector} + .dropdown",
                f"{selector} .dropdown-menu",
                "[role='tooltip']:visible",
                ".tooltip:visible",
                ".dropdown:visible"
            ]
            
            for dd_selector in dropdown_selectors:
                try:
                    elements = self.page.locator(dd_selector)
                    count = await elements.count()
                    if count > 0:
                        for i in range(min(count, 5)):  # Limit to 5 elements
                            elem = elements.nth(i)
                            if await elem.is_visible():
                                text = await elem.inner_text()
                                result["newly_visible_elements"].append({
                                    "selector": dd_selector,
                                    "text": text[:200]
                                })
                except:
                    pass
            
            result["success"] = True
            print(f"Hover successful: {visible_after - visible_before} new elements visible")
            
        except PlaywrightTimeoutError:
            result["error"] = f"Selector not found or not visible: {selector}"
            print(f"Timeout: {selector} not found")
        except Exception as e:
            result["error"] = str(e)
            print(f"Hover error: {str(e)}")
        
        return result
    
    async def _wait_for_element_with_retry(self, selector: str, timeout: int = 10000):
        """Try multiple strategies to find an element."""
        strategies = [
            selector,  # Original selector
            f"visible=true >> {selector}",  # Only visible elements
        ]
        
        for strategy in strategies:
            try:
                element = self.page.locator(strategy).first
                await element.wait_for(state="visible", timeout=timeout // len(strategies))
                return element
            except:
                continue
        
        # If all strategies fail, try the original one last time with full timeout
        element = self.page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        return element
    
    async def _execute_click(self, selector: str) -> Dict[str, Any]:
        """
        Execute click action and detect popups/modals.
        
        Args:
            selector: CSS selector to click
            
        Returns:
            Dictionary with click results
        """
        result = {
            "action": "click",
            "selector": selector,
            "success": False,
            "popup_detected": False,
            "popup_details": {},
            "url_changed": False,
            "url_before": "",
            "url_after": ""
        }
        
        try:
            # Capture URL before click
            result["url_before"] = self.page.url
            
            # Wait for element and click with retry
            element = await self._wait_for_element_with_retry(selector, timeout=10000)
            await element.click()
            
            # Wait longer for popup/modal to appear and stabilize
            await self.page.wait_for_timeout(2500)
            
            # Capture URL after click
            result["url_after"] = self.page.url
            result["url_changed"] = result["url_before"] != result["url_after"]
            
            # Check for common popup/modal patterns
            modal_selectors = [
                "[role='dialog']",
                "[aria-modal='true']",
                ".modal",
                ".popup",
                ".modal.show",
                ".modal-dialog",
                "[class*='modal']",
                "[class*='popup']",
                "[class*='dialog']",
                "div[style*='display: block']"
            ]
            
            popup_found = False
            for modal_selector in modal_selectors:
                try:
                    # Wait a bit for modal to fully render
                    await self.page.wait_for_timeout(500)
                    
                    modal = self.page.locator(modal_selector).first
                    if await modal.is_visible():
                        popup_found = True
                        result["popup_detected"] = True
                        
                        # Extract popup details
                        result["popup_details"]["selector"] = modal_selector
                        
                        # Try to get title - look in the modal context
                        try:
                            title_selectors = [
                                f"{modal_selector} h1",
                                f"{modal_selector} h2",
                                f"{modal_selector} h3",
                                f"{modal_selector} .modal-title",
                                f"{modal_selector} .popup-title",
                                f"{modal_selector} [role='heading']",
                                f"{modal_selector} .title",
                                f"{modal_selector} strong:first-of-type"
                            ]
                            for title_sel in title_selectors:
                                try:
                                    title_elem = self.page.locator(title_sel).first
                                    await title_elem.wait_for(state="visible", timeout=1000)
                                    result["popup_details"]["title"] = await title_elem.inner_text()
                                    break
                                except:
                                    continue
                        except:
                            pass
                        
                        # Try to get ALL buttons and links in the popup
                        try:
                            # Look for buttons, links, and clickable elements
                            clickable_selectors = [
                                f"{modal_selector} button",
                                f"{modal_selector} a",
                                f"{modal_selector} [role='button']",
                                f"{modal_selector} .btn",
                                f"{modal_selector} input[type='button']"
                            ]
                            
                            button_info = []
                            for click_sel in clickable_selectors:
                                try:
                                    elements = self.page.locator(click_sel)
                                    count = await elements.count()
                                    for i in range(count):
                                        elem = elements.nth(i)
                                        if await elem.is_visible():
                                            text = await elem.inner_text()
                                            # Also get aria-label if available
                                            aria_label = await elem.get_attribute("aria-label")
                                            class_name = await elem.get_attribute("class")
                                            
                                            button_info.append({
                                                "text": text.strip(),
                                                "aria_label": aria_label,
                                                "class": class_name,
                                                "selector": click_sel
                                            })
                                except:
                                    continue
                            
                            result["popup_details"]["buttons"] = button_info[:10]  # Limit to 10
                        except:
                            pass
                        
                        # Get popup full content
                        try:
                            content = await modal.inner_text()
                            result["popup_details"]["content_preview"] = content[:1000]
                        except:
                            pass
                        
                        # Capture popup HTML for better selector generation
                        try:
                            popup_html = await modal.inner_html()
                            result["popup_details"]["html_snippet"] = popup_html[:2000]
                        except:
                            pass
                        
                        break  # Found a popup, stop searching
                        
                except:
                    pass
            
            result["success"] = True
            
            if popup_found:
                print(f"Click successful: Popup detected")
            elif result["url_changed"]:
                print(f"Click successful: URL changed to {result['url_after']}")
            else:
                print(f"Click successful: No popup or URL change detected")
            
        except PlaywrightTimeoutError:
            result["error"] = f"Selector not found or not visible: {selector}"
            print(f"Timeout: {selector} not found")
        except Exception as e:
            result["error"] = str(e)
            print(f"Click error: {str(e)}")
        
        return result


async def execute_actions(url: str, action_plan: List[Dict[str, Any]], headless: bool = True) -> Dict[str, Any]:
    """
    Convenience function to execute action plan.
    
    Args:
        url: URL to navigate to
        action_plan: List of actions to execute
        headless: Whether to run in headless mode
        
    Returns:
        Execution results dictionary
    """
    agent = PlaywrightAgent(headless=headless)
    return await agent.execute_action_plan(url, action_plan)

