"""
JavaScript Renderer

This module provides functionality to render JavaScript-heavy websites
using Playwright for accurate content extraction.

Enhancements:
- Improved waiting strategies for dynamic content
- Better error handling and retry logic
- Resource usage monitoring and optimization
- Custom browser configuration
"""
import os
import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

class JavaScriptRenderer:
    """Render JavaScript-heavy websites using Playwright."""
    
    def __init__(self, **kwargs):
        """
        Initialize the JavaScript renderer.
        
        Args:
            browser_type: Browser to use (chromium, firefox, webkit)
            headless: Whether to run the browser in headless mode
            viewport: Viewport dimensions (width, height)
            timeout: Timeout for page operations in milliseconds
            user_agent: User agent string
            screenshot_dir: Directory to save screenshots
            wait_strategies: List of waiting strategies to use
            max_retries: Maximum number of retries for failed renderings
            retry_delay: Delay in seconds between retries
            javascript_enabled: Whether to enable JavaScript
            intercept_requests: Whether to intercept and filter requests
        """
        self.browser_type = kwargs.get('browser_type', 'chromium')
        self.headless = kwargs.get('headless', True)
        self.viewport = kwargs.get('viewport', {'width': 1280, 'height': 800})
        self.timeout = kwargs.get('timeout', 30000)  # milliseconds
        self.user_agent = kwargs.get('user_agent', 'WebsiteCrawlerBot/1.0 (Playwright)')
        self.screenshot_dir = kwargs.get('screenshot_dir', None)
        self.wait_strategies = kwargs.get('wait_strategies', ['networkidle', 'load', 'domcontentloaded'])
        self.max_retries = kwargs.get('max_retries', 2)
        self.retry_delay = kwargs.get('retry_delay', 1)  # seconds
        self.javascript_enabled = kwargs.get('javascript_enabled', True)
        self.intercept_requests = kwargs.get('intercept_requests', False)
        
        # Create screenshot directory if needed
        if self.screenshot_dir:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            
        # Internal state
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        """Initialize Playwright and browser on context enter."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser and Playwright on context exit."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize Playwright and launch browser."""
        try:
            self.playwright = await async_playwright().start()
            
            # Select browser based on configuration
            if self.browser_type == 'firefox':
                browser_factory = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_factory = self.playwright.webkit
            else:
                browser_factory = self.playwright.chromium
            
            # Launch browser with appropriate options
            self.browser = await browser_factory.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            
            # Create browser context with our settings
            self.context = await self.browser.new_context(
                viewport=self.viewport,
                user_agent=self.user_agent,
                java_script_enabled=self.javascript_enabled,
                bypass_csp=True,  # Bypass Content Security Policy to ensure scripts run
                ignore_https_errors=True  # Ignore HTTPS errors
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.timeout)
            
            logger.info(f"Initialized {self.browser_type} browser in {'headless' if self.headless else 'headed'} mode")
            return True
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            await self.cleanup()
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def filter_requests(self, route, request):
        """Filter requests to block ads, trackers, etc."""
        # Block common ad/tracking domains
        blocked_domains = [
            'googleads', 'doubleclick.net', 'facebook.com/tr', 
            'analytics', 'tracking', 'adservice', 'pixel'
        ]
        
        # Block unnecessary resource types to speed up rendering
        if request.resource_type in ['image', 'media', 'font']:
            await route.abort()
            return
            
        # Check if the URL contains any blocked domains
        url = request.url.lower()
        if any(domain in url for domain in blocked_domains):
            await route.abort()
            return
            
        # Continue with the request
        await route.continue_()
    
    async def wait_for_page_load(self, page, strategy: str) -> bool:
        """Wait for a page to load using the specified strategy."""
        try:
            if strategy == 'networkidle':
                await page.wait_for_load_state('networkidle')
            elif strategy == 'load':
                await page.wait_for_load_state('load')
            elif strategy == 'domcontentloaded':
                await page.wait_for_load_state('domcontentloaded')
            elif strategy == 'visible':
                # Wait for the main content to be visible
                # Adjust the selector based on common content containers
                for selector in ['main', 'article', '#content', '.content', '.main', 'body']:
                    try:
                        await page.wait_for_selector(selector, state='visible', timeout=5000)
                        break
                    except PlaywrightTimeoutError:
                        continue
            elif strategy == 'animation':
                # Give time for animations to complete
                await asyncio.sleep(2)
            elif strategy == 'custom':
                # Wait for an additional fixed time
                await asyncio.sleep(3)
            else:
                logger.warning(f"Unknown waiting strategy: {strategy}")
                return False
                
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout while waiting with strategy: {strategy}")
            return False
        except Exception as e:
            logger.error(f"Error while waiting with strategy {strategy}: {str(e)}")
            return False
    
    async def wait_for_content(self, page):
        """Wait for content to load using multiple strategies."""
        # Try each waiting strategy in sequence
        for strategy in self.wait_strategies:
            success = await self.wait_for_page_load(page, strategy)
            if not success:
                logger.warning(f"Strategy {strategy} failed or timed out")
        
        # Additional heuristic: wait for the page to stabilize
        # This helps with sites that keep loading content
        try:
            # Get the page height after initial load
            initial_height = await page.evaluate('document.body.scrollHeight')
            
            # Wait a bit and check if page height has changed
            for _ in range(3):
                await asyncio.sleep(1)
                new_height = await page.evaluate('document.body.scrollHeight')
                
                # If height hasn't changed, page is probably stable
                if new_height == initial_height:
                    break
                    
                initial_height = new_height
        except Exception as e:
            logger.warning(f"Error during stabilization check: {str(e)}")
    
    async def save_screenshot(self, page, url: str):
        """Save a screenshot of the rendered page."""
        if not self.screenshot_dir:
            return None
            
        try:
            # Create a safe filename based on the URL
            filename = f"screenshot_{hash(url) & 0xffffffff}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Take screenshot of the full page
            await page.screenshot(path=filepath, full_page=True)
            logger.info(f"Screenshot saved to {filepath}")
            
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None
    
    async def extract_page_metadata(self, page) -> Dict[str, Any]:
        """Extract metadata from the rendered page."""
        try:
            metadata = await page.evaluate('''() => {
                const metadata = {};
                
                // Get title
                metadata.title = document.title;
                
                // Get meta tags
                const metaTags = {};
                document.querySelectorAll('meta').forEach(meta => {
                    const name = meta.getAttribute('name') || meta.getAttribute('property');
                    const content = meta.getAttribute('content');
                    if (name && content) {
                        metaTags[name] = content;
                    }
                });
                metadata.meta = metaTags;
                
                // Get canonical URL
                const canonical = document.querySelector('link[rel="canonical"]');
                if (canonical) {
                    metadata.canonical = canonical.getAttribute('href');
                }
                
                // Check if it's a single-page application
                metadata.isSPA = (
                    typeof angular !== 'undefined' || 
                    typeof React !== 'undefined' || 
                    typeof Vue !== 'undefined' || 
                    document.querySelector('[ng-app]') !== null ||
                    document.querySelector('[data-reactroot]') !== null
                );
                
                // Get open graph data
                const openGraph = {};
                document.querySelectorAll('meta[property^="og:"]').forEach(meta => {
                    const property = meta.getAttribute('property');
                    const content = meta.getAttribute('content');
                    if (property && content) {
                        openGraph[property.replace('og:', '')] = content;
                    }
                });
                metadata.openGraph = openGraph;
                
                // Get schema.org data
                metadata.schemaOrg = [];
                document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                    try {
                        const data = JSON.parse(script.textContent);
                        metadata.schemaOrg.push(data);
                    } catch (e) {
                        // Ignore parsing errors
                    }
                });
                
                return metadata;
            }''')
            
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {}
    
    async def render_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Render a page with JavaScript and extract content.
        
        Args:
            url: URL to render
            **kwargs: Additional options that override instance settings
            
        Returns:
            Dict containing rendered content and metadata
        """
        # Check if we need to initialize
        if not self.browser:
            success = await self.initialize()
            if not success:
                return {"success": False, "error": "Failed to initialize browser"}
        
        # Override instance settings with any provided kwargs
        timeout = kwargs.get('timeout', self.timeout)
        wait_strategies = kwargs.get('wait_strategies', self.wait_strategies)
        take_screenshot = kwargs.get('take_screenshot', bool(self.screenshot_dir))
        
        # Retry logic for reliability
        for attempt in range(self.max_retries + 1):
            page = None
            try:
                # Create a new page
                page = await self.context.new_page()
                
                # Set up request interception if enabled
                if self.intercept_requests:
                    await page.route('**/*', self.filter_requests)
                
                # Track start time for performance monitoring
                start_time = time.time()
                
                # Navigate to the URL
                logger.info(f"Rendering {url} (attempt {attempt+1}/{self.max_retries+1})")
                response = await page.goto(url, wait_until='commit', timeout=timeout)
                
                # Check if navigation was successful
                if not response:
                    logger.warning(f"No response received for {url}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return {"success": False, "error": "No response received"}
                
                # Check status code
                status_code = response.status
                if status_code >= 400:
                    logger.warning(f"HTTP error {status_code} for {url}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return {"success": False, "error": f"HTTP error {status_code}"}
                
                # Wait for the page content to load
                await self.wait_for_content(page)
                
                # Get the rendered HTML
                html = await page.content()
                
                # Get page title
                title = await page.title()
                
                # Extract text content
                text_content = await page.evaluate('''() => {
                    const paragraphs = Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li'))
                        .map(el => el.textContent.trim())
                        .filter(text => text.length > 0);
                    return paragraphs.join('\\n\\n');
                }''')
                
                # Extract links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => {
                            return {
                                url: a.href,
                                text: a.textContent.trim(),
                                isExternal: a.host !== window.location.host
                            };
                        })
                        .filter(link => 
                            link.url.startsWith('http') && 
                            !link.url.startsWith('javascript:') && 
                            !link.url.includes('#')
                        );
                }''')
                
                # Extract images
                images = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('img[src]'))
                        .map(img => {
                            return {
                                url: img.src,
                                alt: img.alt || '',
                                width: img.width || null,
                                height: img.height || null
                            };
                        })
                        .filter(img => img.url && img.url.trim().length > 0);
                }''')
                
                # Extract metadata
                metadata = await self.extract_page_metadata(page)
                
                # Take screenshot if requested
                screenshot_path = None
                if take_screenshot:
                    screenshot_path = await self.save_screenshot(page, url)
                
                # Calculate render time
                render_time = time.time() - start_time
                
                # Success result
                result = {
                    "success": True,
                    "url": url,
                    "final_url": page.url,  # May differ from original URL due to redirects
                    "status_code": status_code,
                    "title": title,
                    "html": html,
                    "text": text_content,
                    "links": links,
                    "images": images,
                    "metadata": metadata,
                    "render_time": render_time,
                }
                
                if screenshot_path:
                    result["screenshot"] = screenshot_path
                
                logger.info(f"Successfully rendered {url} in {render_time:.2f}s")
                return result
                
            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout rendering {url}: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {"success": False, "error": f"Timeout: {str(e)}"}
                
            except Exception as e:
                logger.error(f"Error rendering {url}: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {"success": False, "error": str(e)}
                
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.warning(f"Error closing page: {str(e)}")
        
        # If we get here, all retries failed
        return {"success": False, "error": "All rendering attempts failed"}

async def render_with_playwright(url: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to render a single page with Playwright.
    
    Args:
        url: The URL to render
        **kwargs: Options for the JavaScriptRenderer
        
    Returns:
        Dict containing rendered content and metadata
    """
    async with JavaScriptRenderer(**kwargs) as renderer:
        return await renderer.render_page(url)
    
async def render_multiple_pages(urls: List[str], **kwargs) -> List[Dict[str, Any]]:
    """
    Render multiple pages with the same JavaScriptRenderer instance.
    
    Args:
        urls: List of URLs to render
        **kwargs: Options for the JavaScriptRenderer
        
    Returns:
        List of dicts containing rendered content and metadata
    """
    results = []
    
    async with JavaScriptRenderer(**kwargs) as renderer:
        for url in urls:
            result = await renderer.render_page(url)
            results.append(result)
            
    return results
