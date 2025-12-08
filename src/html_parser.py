"""
HTML Parser Module
Uses Playwright to load webpage and BeautifulSoup for HTML extraction.
Supports caching to save time during development.
"""

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import Tuple
from cache import get_cache


class HTMLParser:
    """Extracts HTML from a webpage using Playwright and BeautifulSoup."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the HTML parser.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
    
    async def extract_html(self, url: str, wait_time: int = 2000, use_cache: bool = True) -> Tuple[str, BeautifulSoup]:
        """
        Load URL using Playwright and extract HTML.
        
        Args:
            url: The URL to load
            wait_time: Time to wait for page load in milliseconds (default: 2000)
            use_cache: Whether to use cached HTML if available (default: True)
            
        Returns:
            Tuple of (raw_html_string, beautifulsoup_object)
            
        Raises:
            Exception: If page loading fails
        """
        # Check cache first
        cache = get_cache() if use_cache else None
        if cache:
            cached_html = cache.get_html(url)
            if cached_html:
                soup = BeautifulSoup(cached_html, 'lxml')
                return cached_html, soup
        
        try:
            async with async_playwright() as playwright:
                # Launch browser
                browser = await playwright.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to URL
                print(f"Loading URL: {url}")
                await page.goto(url, wait_until="domcontentloaded")
                
                # Wait for additional resources to load
                await page.wait_for_timeout(wait_time)
                
                # Extract HTML content
                raw_html = await page.content()
                
                # Close browser
                await context.close()
                await browser.close()
                
                # Parse with BeautifulSoup for minimal cleanup
                soup = BeautifulSoup(raw_html, 'lxml')
                
                print(f"Successfully extracted HTML ({len(raw_html)} characters)")
                
                # Cache the HTML
                if cache:
                    cache.set_html(url, raw_html)
                
                return raw_html, soup
                
        except Exception as e:
            raise Exception(f"Failed to extract HTML from {url}: {str(e)}")


async def load_html(url: str, headless: bool = True, use_cache: bool = True) -> Tuple[str, BeautifulSoup]:
    """
    Convenience function to load HTML from a URL.
    
    Args:
        url: The URL to load
        headless: Whether to run browser in headless mode
        use_cache: Whether to use cached HTML (default: True)
        
    Returns:
        Tuple of (raw_html_string, beautifulsoup_object)
    """
    parser = HTMLParser(headless=headless)
    return await parser.extract_html(url, use_cache=use_cache)

