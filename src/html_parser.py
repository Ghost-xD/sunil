"""
HTML Parser Module
Uses Playwright to load webpage and BeautifulSoup for HTML extraction.
"""

from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from typing import Tuple


class HTMLParser:
    """Extracts HTML from a webpage using Playwright and BeautifulSoup."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the HTML parser.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
    
    def extract_html(self, url: str, wait_time: int = 2000) -> Tuple[str, BeautifulSoup]:
        """
        Load URL using Playwright and extract HTML.
        
        Args:
            url: The URL to load
            wait_time: Time to wait for page load in milliseconds (default: 2000)
            
        Returns:
            Tuple of (raw_html_string, beautifulsoup_object)
            
        Raises:
            Exception: If page loading fails
        """
        try:
            with sync_playwright() as playwright:
                # Launch browser
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                
                # Navigate to URL
                print(f"Loading URL: {url}")
                page.goto(url, wait_until="domcontentloaded")
                
                # Wait for additional resources to load
                page.wait_for_timeout(wait_time)
                
                # Extract HTML content
                raw_html = page.content()
                
                # Close browser
                context.close()
                browser.close()
                
                # Parse with BeautifulSoup for minimal cleanup
                soup = BeautifulSoup(raw_html, 'lxml')
                
                print(f"Successfully extracted HTML ({len(raw_html)} characters)")
                
                return raw_html, soup
                
        except Exception as e:
            raise Exception(f"Failed to extract HTML from {url}: {str(e)}")


def load_html(url: str, headless: bool = True) -> Tuple[str, BeautifulSoup]:
    """
    Convenience function to load HTML from a URL.
    
    Args:
        url: The URL to load
        headless: Whether to run browser in headless mode
        
    Returns:
        Tuple of (raw_html_string, beautifulsoup_object)
    """
    parser = HTMLParser(headless=headless)
    return parser.extract_html(url)

