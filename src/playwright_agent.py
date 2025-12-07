"""
Playwright Agent Module
Executes action plans and captures results without interpretation.
"""

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Any
import time


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
    
    def start_browser(self, url: str):
        """Start browser and navigate to URL."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        print(f"Navigating to: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(2000)  # Wait for initial load
    
    def close_browser(self):
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def execute_action_plan(self, url: str, action_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            self.start_browser(url)
            
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
                        result = self._execute_hover(selector)
                        action_result["success"] = result["success"]
                        action_result["details"] = result
                        if result["success"]:
                            results["hover_results"].append(result)
                    
                    elif action == "click":
                        result = self._execute_click(selector)
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
            self.close_browser()
        
        return results
    
    def _execute_hover(self, selector: str) -> Dict[str, Any]:
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
            visible_before = self.page.locator("*:visible").count()
            result["element_count_before"] = visible_before
            
            # Wait for element and hover
            element = self.page.locator(selector).first
            element.wait_for(state="visible", timeout=5000)
            element.hover()
            
            # Wait for any animations
            self.page.wait_for_timeout(1000)
            
            # Get visible elements count after hover
            visible_after = self.page.locator("*:visible").count()
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
                    count = elements.count()
                    if count > 0:
                        for i in range(min(count, 5)):  # Limit to 5 elements
                            elem = elements.nth(i)
                            if elem.is_visible():
                                text = elem.inner_text()[:200]  # Limit text length
                                result["newly_visible_elements"].append({
                                    "selector": dd_selector,
                                    "text": text
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
    
    def _execute_click(self, selector: str) -> Dict[str, Any]:
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
            
            # Wait for element and click
            element = self.page.locator(selector).first
            element.wait_for(state="visible", timeout=5000)
            element.click()
            
            # Wait for potential popup/navigation
            self.page.wait_for_timeout(1500)
            
            # Capture URL after click
            result["url_after"] = self.page.url
            result["url_changed"] = result["url_before"] != result["url_after"]
            
            # Check for common popup/modal patterns
            modal_selectors = [
                "[role='dialog']",
                ".modal:visible",
                ".popup:visible",
                "[aria-modal='true']",
                ".modal.show",
                ".modal-dialog"
            ]
            
            popup_found = False
            for modal_selector in modal_selectors:
                try:
                    modal = self.page.locator(modal_selector).first
                    if modal.is_visible():
                        popup_found = True
                        result["popup_detected"] = True
                        
                        # Extract popup details
                        result["popup_details"]["selector"] = modal_selector
                        
                        # Try to get title
                        try:
                            title_selectors = [
                                f"{modal_selector} h1",
                                f"{modal_selector} h2",
                                f"{modal_selector} .modal-title",
                                f"{modal_selector} [role='heading']"
                            ]
                            for title_sel in title_selectors:
                                title_elem = self.page.locator(title_sel).first
                                if title_elem.is_visible():
                                    result["popup_details"]["title"] = title_elem.inner_text()
                                    break
                        except:
                            pass
                        
                        # Try to get buttons
                        try:
                            buttons = self.page.locator(f"{modal_selector} button")
                            button_count = buttons.count()
                            button_texts = []
                            for i in range(min(button_count, 5)):  # Limit to 5 buttons
                                btn = buttons.nth(i)
                                if btn.is_visible():
                                    button_texts.append(btn.inner_text())
                            result["popup_details"]["buttons"] = button_texts
                        except:
                            pass
                        
                        # Get popup content (limited)
                        try:
                            content = modal.inner_text()[:500]  # Limit content length
                            result["popup_details"]["content_preview"] = content
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


def execute_actions(url: str, action_plan: List[Dict[str, Any]], headless: bool = True) -> Dict[str, Any]:
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
    return agent.execute_action_plan(url, action_plan)

