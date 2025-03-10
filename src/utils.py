"""
Utility Functions

This module provides various utility functions for the web crawler,
including URL validation, content manipulation, and monitoring tools.

Enhancements:
- Improved URL validation and normalization
- Monitoring dashboard capabilities
- Advanced text processing utilities
- Rate limiting helpers
"""
import os
import re
import time
import json
import logging
import hashlib
from typing import Dict, List, Set, Any, Optional, Tuple, Union
from urllib.parse import urlparse, urlunparse, urljoin, parse_qs, urlencode
from datetime import datetime, timedelta
import validators
from bs4 import BeautifulSoup
import asyncio

logger = logging.getLogger(__name__)

# URL UTILITIES
def normalize_url(url: str, base_url=None) -> str:
    """
    Normalize a URL to avoid crawling duplicates.
    
    - Convert to lowercase
    - Remove default ports (80 for HTTP, 443 for HTTPS)
    - Remove fragments
    - Sort query parameters
    - Remove trailing slashes
    """
    try:
        # Parse the URL
        parsed = urlparse(url)
    
        # Lowercase the scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if (scheme == 'http' and netloc.endswith(':80')) or (scheme == 'https' and netloc.endswith(':443')):
            netloc = netloc.rsplit(':', 1)[0]
    
        # Sort query parameters
        if parsed.query:
            query_params = parse_qs(parsed.query)
            # Sort the params and rebuild the query string
            sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        else:
            sorted_query = ''
        
        # Rebuild the URL without fragments and with sorted query
        normalized = urlunparse((
            scheme,
            netloc,
            parsed.path.rstrip('/') or '/',  # Remove trailing slash but keep a single slash for root
            parsed.params,
            sorted_query,
            ''  # Remove fragment
        ))
        
        return normalized
    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {str(e)}")
        return url

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid and crawlable.
    
    - Must be a valid URL format
    - Must have an allowed scheme (http, https)
    - Must not be a common file type to skip
    """
    if not url:
        return False
    
    # Check basic URL validity
    if not validators.url(url):
        return False
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        return False
    
    # Check for common file extensions to skip
    path = parsed.path.lower()
    skip_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar', 
                      '.gz', '.mp3', '.mp4', '.avi', '.mov', '.webp', '.svg']
    
    if any(path.endswith(ext) for ext in skip_extensions):
        return False
    
    return True

def get_domain_from_url(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc

def urls_have_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs have the same domain."""
    return get_domain_from_url(url1) == get_domain_from_url(url2)

def is_subpath(base_url: str, url: str) -> bool:
    """Check if a URL is a subpath of a base URL."""
    parsed_base = urlparse(base_url)
    parsed_url = urlparse(url)
    
    # Different domains
    if parsed_base.netloc != parsed_url.netloc:
        return False
    
    # Check if the path is a subpath
    base_path = parsed_base.path.rstrip('/')
    url_path = parsed_url.path.rstrip('/')
    
    return url_path.startswith(base_path)

# CONTENT UTILITIES
def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
        element.extract()
    
    # Get text and normalize whitespace
    text = soup.get_text(separator=' ')
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def compute_content_hash(content: str) -> str:
    """Compute a hash of the content for diffing."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def generate_filename_from_url(url: str, extension: str = "html") -> str:
    """Generate a safe filename from a URL."""
    # Parse the URL to get path
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Replace path delimiters with underscores
    safe_name = re.sub(r'[^\w\-\.]', '_', path)
    
    # Use domain as prefix if path is empty
    if not safe_name:
        safe_name = re.sub(r'[^\w\-\.]', '_', parsed.netloc)
    
    # Add a hash of the full URL to ensure uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    
    # Combine everything
    filename = f"{safe_name}_{url_hash}.{extension}"
    
    # Ensure filename doesn't exceed max length for filesystems
    if len(filename) > 255:
        filename = f"{url_hash}.{extension}"
    
    return filename

# MONITORING UTILITIES
class CrawlerStats:
    """Class to track and report crawler statistics."""
    
    def __init__(self):
        """Initialize the statistics container."""
        self.start_time = time.time()
        self.stats = {
            "pages": {
                "crawled": 0,
                "skipped": 0,
                "failed": 0,
                "queued": 0
            },
            "requests": {
                "total": 0,
                "success": 0,
                "error": 0,
                "timeout": 0,
                "retry": 0
            },
            "content": {
                "total_bytes": 0,
                "html_pages": 0,
                "non_html": 0,
                "images_found": 0,
                "links_found": 0
            },
            "performance": {
                "avg_request_time": 0,
                "peak_memory_mb": 0,
                "crawl_rate_pages_per_min": 0
            },
            "timing": {
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "elapsed_seconds": 0
            }
        }
        self.request_times = []
    
    def update_page_stat(self, stat_name: str, increment: int = 1):
        """Update a page-related statistic."""
        if stat_name in self.stats["pages"]:
            self.stats["pages"][stat_name] += increment
    
    def update_request_stat(self, stat_name: str, increment: int = 1):
        """Update a request-related statistic."""
        if stat_name in self.stats["requests"]:
            self.stats["requests"][stat_name] += increment
    
    def add_request_time(self, seconds: float):
        """Add a request time measurement and update the average."""
        self.request_times.append(seconds)
        avg = sum(self.request_times) / len(self.request_times)
        self.stats["performance"]["avg_request_time"] = avg
    
    def update_content_stat(self, stat_name: str, increment: int = 1):
        """Update a content-related statistic."""
        if stat_name in self.stats["content"]:
            self.stats["content"][stat_name] += increment
    
    def update_crawl_rate(self):
        """Update the crawl rate calculation."""
        elapsed_mins = (time.time() - self.start_time) / 60
        if elapsed_mins > 0:
            pages_crawled = self.stats["pages"]["crawled"]
            rate = pages_crawled / elapsed_mins
            self.stats["performance"]["crawl_rate_pages_per_min"] = rate
    
    def finalize_stats(self):
        """Update final statistics when crawl is complete."""
        end_time = time.time()
        elapsed = end_time - self.start_time
        
        self.stats["timing"]["end_time"] = datetime.now().isoformat()
        self.stats["timing"]["elapsed_seconds"] = elapsed
        
        self.update_crawl_rate()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the statistics."""
        self.update_crawl_rate()
        
        elapsed = time.time() - self.start_time
        self.stats["timing"]["elapsed_seconds"] = elapsed
        
        # Calculate a few derived stats
        pages_crawled = self.stats["pages"]["crawled"]
        total_requests = self.stats["requests"]["total"]
        success_rate = 0
        if total_requests > 0:
            success_rate = (self.stats["requests"]["success"] / total_requests) * 100
        
        summary = {
            "pages_crawled": pages_crawled,
            "elapsed_time": timedelta(seconds=int(elapsed)),
            "crawl_rate": self.stats["performance"]["crawl_rate_pages_per_min"],
            "success_rate": success_rate,
            "avg_request_time": self.stats["performance"]["avg_request_time"],
            "failed_pages": self.stats["pages"]["failed"]
        }
        
        return summary
    
    def save_stats(self, filepath: str):
        """Save statistics to a JSON file."""
        self.finalize_stats()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.stats, f, indent=2)
            logger.info(f"Statistics saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving statistics: {str(e)}")
            return False

class RateLimiter:
    """Rate limiting utility for domains."""
    
    def __init__(self, requests_per_minute: int = 30):
        """
        Initialize rate limiter.
    
    Args:
            requests_per_minute: Maximum requests per minute per domain
        """
        self.requests_per_minute = requests_per_minute
        self.interval = 60 / requests_per_minute  # seconds between requests
        self.domain_last_request = {}  # domain -> timestamp
    
    async def wait_if_needed(self, domain: str) -> float:
        """
        Wait if necessary to maintain rate limit for the domain.
        
        Returns the number of seconds waited.
        """
        current_time = time.time()
        wait_time = 0
        
        if domain in self.domain_last_request:
            elapsed = current_time - self.domain_last_request[domain]
            if elapsed < self.interval:
                wait_time = self.interval - elapsed
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Update last request time
        self.domain_last_request[domain] = time.time()
        
        return wait_time
    
    def get_current_rate(self, domain: str) -> float:
        """Get the current request rate for a domain in requests per minute."""
        if domain not in self.domain_last_request:
            return 0
            
        elapsed = time.time() - self.domain_last_request[domain]
        if elapsed < 1:  # avoid division by zero or very small numbers
            elapsed = 1
            
        # Estimate based on the time since last request
        current_rate = 60 / elapsed
        
        return min(current_rate, self.requests_per_minute)

class CrawlerDashboard:
    """Simple dashboard to monitor crawler progress."""
    
    def __init__(self, stats: CrawlerStats, update_interval: int = 5):
        """
        Initialize the dashboard.
        
        Args:
            stats: CrawlerStats instance to monitor
            update_interval: Update interval in seconds
        """
        self.stats = stats
        self.update_interval = update_interval
        self.running = False
    
    def start(self):
        """Start the dashboard in a separate thread."""
        self.running = True
        self.thread = asyncio.create_task(self._run_dashboard())
    
    async def stop(self):
        """Stop the dashboard."""
        self.running = False
        if self.thread:
            await self.thread
    
    async def _run_dashboard(self):
        """Run the dashboard loop."""
        try:
            import os
            clear_command = 'cls' if os.name == 'nt' else 'clear'
            
            while self.running:
                # Clear the screen
                os.system(clear_command)
                
                # Update crawl rate
                self.stats.update_crawl_rate()
    
                # Get summary
                summary = self.stats.get_summary()
                
                # Print dashboard
                print("\n" + "=" * 50)
                print("CRAWLER DASHBOARD")
                print("=" * 50)
                
                print(f"\nRunning for: {summary['elapsed_time']}")
                print(f"Pages crawled: {summary['pages_crawled']}")
                print(f"Pages failed: {summary['failed_pages']}")
                print(f"Crawl rate: {summary['crawl_rate']:.2f} pages/minute")
                print(f"Success rate: {summary['success_rate']:.1f}%")
                print(f"Avg request time: {summary['avg_request_time']:.2f} seconds")
                
                print("\n" + "-" * 50)
                print("QUEUES")
                print(f"Pages queued: {self.stats.stats['pages']['queued']}")
                print(f"Pages skipped: {self.stats.stats['pages']['skipped']}")
                
                print("\n" + "-" * 50)
                print("CONTENT")
                print(f"Links found: {self.stats.stats['content']['links_found']}")
                print(f"Images found: {self.stats.stats['content']['images_found']}")
                print(f"HTML pages: {self.stats.stats['content']['html_pages']}")
                print(f"Total bytes: {self.stats.stats['content']['total_bytes'] / 1024:.2f} KB")
                
                print("\n" + "=" * 50)
                print("Press Ctrl+C to stop the crawler")
                print("=" * 50)
                
                # Sleep before next update
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")

class ResourceExtractor:
    """Extracts and categorizes resources from HTML content."""
    
    def __init__(self, base_url, output_dir):
        self.base_url = base_url
        self.output_dir = output_dir
        self.css_dir = os.path.join(output_dir, "css")
        self.js_dir = os.path.join(output_dir, "js")
        self.fonts_dir = os.path.join(output_dir, "fonts")
        os.makedirs(self.css_dir, exist_ok=True)
        os.makedirs(self.js_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)
        
    def extract_stylesheets(self, html_content, page_url):
        """Extract all CSS stylesheets from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        stylesheets = []
        
        # Find all external CSS files
        for link in soup.find_all('link', rel='stylesheet'):
            if 'href' in link.attrs:
                css_url = normalize_url(link['href'], page_url)
                if css_url:
                    stylesheets.append(css_url)
                    
        # Find all inline styles and save them
        for style in soup.find_all('style'):
            # Handle inline styles if needed
            pass
            
        return stylesheets
        
    def extract_scripts(self, html_content, page_url):
        """Extract all JavaScript files from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = []
        
        for script in soup.find_all('script', src=True):
            js_url = normalize_url(script['src'], page_url)
            if js_url:
                scripts.append(js_url)
                
        return scripts
        
    async def download_resource(self, url, output_path, session):
        """Download a resource and save it to the specified path."""
        try:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    content = await response.read()
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    return True, url, len(content)
                else:
                    logging.warning(f"Failed to download {url}: HTTP {response.status}")
                    return False, url, 0
        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            return False, url, 0
            
    def get_local_path(self, url, resource_type):
        """Generate a local path for a downloaded resource."""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"resource_{hash(url)}"
            
        if resource_type == 'css':
            return os.path.join(self.css_dir, filename)
        elif resource_type == 'js':
            return os.path.join(self.js_dir, filename)
        elif resource_type == 'font':
            return os.path.join(self.fonts_dir, filename)
        else:
            return None

    def extract_fonts_from_css(self, css_content, css_url):
        """Extract font URLs from CSS content."""
        fonts = []
        
        # Pattern for font-face src URLs
        import re
        
        # Find all font URLs in the CSS
        # Match url() patterns in font-face declarations
        font_face_pattern = re.compile(r'@font-face\s*{[^}]*?src\s*:\s*[^;]*?url\(([^)]+)\)[^}]*?}', re.DOTALL)
        url_pattern = re.compile(r'url\([\'"]*([^\'"]+)[\'"]?\)', re.DOTALL)
        
        # First look for font-face declarations
        for font_face in font_face_pattern.findall(css_content):
            # Then extract URLs from the font-face src attribute
            for url_match in url_pattern.findall(font_face):
                font_url = normalize_url(url_match, css_url)
                if font_url:
                    fonts.append(font_url)
        
        # Also look for any URL that seems to be a font file
        for url_match in url_pattern.findall(css_content):
            if any(ext in url_match.lower() for ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']):
                font_url = normalize_url(url_match, css_url)
                if font_url and font_url not in fonts:
                    fonts.append(font_url)
        
        return fonts

    async def process_css_for_fonts(self, css_url, css_local_path, session):
        """Download a CSS file and extract any fonts referenced within it."""
        try:
            # Download the CSS file
            success, _, css_size = await self.download_resource(css_url, css_local_path, session)
            
            if success:
                # Read the CSS content
                with open(css_local_path, 'r', encoding='utf-8', errors='ignore') as f:
                    css_content = f.read()
                
                # Extract font URLs
                fonts = self.extract_fonts_from_css(css_content, css_url)
                
                # Download each font
                font_downloads = []
                for font_url in fonts:
                    font_local_path = self.get_local_path(font_url, 'font')
                    if font_local_path:
                        font_downloads.append(self.download_resource(font_url, font_local_path, session))
                
                # Wait for all downloads to complete
                if font_downloads:
                    font_results = await asyncio.gather(*font_downloads, return_exceptions=True)
                    return fonts, font_results
                
            return [], []
        except Exception as e:
            logging.error(f"Error processing CSS for fonts: {e}")
            return [], []

def extract_domain(url):
    """Extract domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc

# Export most useful functions at module level
__all__ = [
    'normalize_url',
    'is_valid_url',
    'get_domain_from_url',
    'urls_have_same_domain',
    'is_subpath',
    'extract_text_from_html',
    'compute_content_hash',
    'generate_filename_from_url',
    'CrawlerStats',
    'RateLimiter',
    'CrawlerDashboard',
    'ResourceExtractor'
]
