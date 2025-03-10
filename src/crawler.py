"""
Website Crawler - Main Crawler Module

This module contains the core functionality for crawling websites and extracting content.

Enhancements:
- Sitemap support for better page discovery
- Improved rate limiting with proper backoff
- Schema.org data extraction
- Content diffing for tracking changes
- Resource cleanup and proper async handling
"""
import os
import re
import time
import json
import asyncio
import logging
import hashlib
import urllib.robotparser
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin, urldefrag

import aiohttp
from bs4 import BeautifulSoup
import validators
from markdownify import markdownify
import tqdm.asyncio
import xml.etree.ElementTree as ET
from aiohttp import ClientTimeout, TCPConnector
from aiohttp.client_exceptions import ClientError

from .utils import normalize_url, extract_domain, CrawlerStats, ResourceExtractor
from .renderer import JSRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebsiteCrawler:
    """Asynchronous website crawler with advanced features."""
    
    def __init__(self, **kwargs):
        """
        Initialize the website crawler.
        
        Args:
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth to crawl
            respect_robots_txt: Whether to respect robots.txt
            rate_limit: Seconds to wait between requests
            user_agent: User agent string to use for requests
            output_formats: List of output formats (markdown, html, json)
            follow_external_links: Whether to follow external links
            timeout: Timeout for requests in seconds
            extract_images: Whether to extract image information
            extract_schema: Whether to extract schema.org data
            cache_dir: Directory to store cache data
            track_changes: Whether to track content changes
            sitemap_discovery: Whether to discover pages via sitemap
            max_file_size: Maximum file size to download (in bytes)
            max_concurrent_requests: Maximum number of concurrent requests
            min_request_interval: Minimum interval between requests to same domain (in seconds)
        """
        # Crawler settings
        self.max_pages = kwargs.get('max_pages', 100)
        self.max_depth = kwargs.get('max_depth', 5)
        self.respect_robots_txt = kwargs.get('respect_robots_txt', True)
        self.rate_limit = kwargs.get('rate_limit', 0.5)
        self.user_agent = kwargs.get('user_agent', "WebsiteCrawlerBot/1.0")
        self.output_formats = kwargs.get('output_formats', ["markdown", "html"])
        self.follow_external_links = kwargs.get('follow_external_links', False)
        self.timeout = kwargs.get('timeout', 30)
        self.extract_images = kwargs.get('extract_images', True)
        self.extract_schema = kwargs.get('extract_schema', True)
        self.cache_dir = kwargs.get('cache_dir', ".cache")
        self.track_changes = kwargs.get('track_changes', True)
        self.sitemap_discovery = kwargs.get('sitemap_discovery', True)
        self.max_file_size = kwargs.get('max_file_size', 10 * 1024 * 1024)  # 10MB
        self.max_concurrent_requests = kwargs.get('max_concurrent_requests', 5)
        self.min_request_interval = kwargs.get('min_request_interval', 1.0)
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # State variables
        self.crawled_urls = set()        # URLs that have been processed
        self.failed_urls = set()         # URLs that failed to process
        self.url_queue = []              # Queue of URLs to process
        self.results = {                 # Results of the crawl
            "pages": {},
            "metadata": {
                "start_time": None,
                "end_time": None,
                "total_pages": 0,
                "failed_pages": 0,
                "settings": {
                    "max_pages": self.max_pages,
                    "max_depth": self.max_depth,
                    "follow_external_links": self.follow_external_links,
                    "extract_images": self.extract_images,
                    "extract_schema": self.extract_schema,
                }
            }
        }
        
        # Domain rate limiting
        self.domain_last_request = {}     # Track last request time per domain
        
        # Robots.txt parsers
        self.robots_parsers = {}          # Cache for robots.txt parsers
        
        # Content cache for diffing
        self.content_cache = self._load_content_cache()
        
        # Domain specific semaphores for rate limiting
        self.domain_semaphores = {}
        
        # Global semaphore for concurrent requests
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Initialize JS renderer if needed
        self.js_rendering = kwargs.get('js_rendering', False)
        if self.js_rendering:
            self.renderer = JSRenderer()
        
        # Initialize resource extractor
        self.resource_extractor = ResourceExtractor(kwargs.get('base_url', ""), kwargs.get('output_dir', "./output"))
    
    def _load_content_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load content cache from disk."""
        cache_file = os.path.join(self.cache_dir, "content_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading content cache: {e}. Starting with empty cache.")
                return {}
        return {}
    
    def _save_content_cache(self) -> None:
        """Save content cache to disk."""
        cache_file = os.path.join(self.cache_dir, "content_cache.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.content_cache, f)
        except IOError as e:
            logger.error(f"Error saving content cache: {e}")
    
    async def fetch_robots_txt(self, base_url: str, session: aiohttp.ClientSession) -> Optional[urllib.robotparser.RobotFileParser]:
        """Fetch and parse robots.txt for a given domain."""
        # Check if we already have a parser for this domain
        if base_url in self.robots_parsers:
            return self.robots_parsers[base_url]
        
        # Parse the base URL to get the domain
        parsed_url = urlparse(base_url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = f"{domain}/robots.txt"
        
        try:
            async with session.get(robots_url, timeout=self.timeout) as response:
                if response.status == 200:
                    robots_txt = await response.text()
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(robots_txt.splitlines())
                    self.robots_parsers[base_url] = parser
                    return parser
                else:
                    logger.warning(f"Failed to fetch robots.txt: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching robots.txt: {str(e)}")
            return None
    
    async def is_allowed_by_robots(self, url: str, session: aiohttp.ClientSession) -> bool:
        """Check if a URL is allowed by robots.txt."""
        if not self.respect_robots_txt:
            return True
            
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        parser = await self.fetch_robots_txt(domain, session)
        if parser:
            return parser.can_fetch(self.user_agent, url)
            
        # If we couldn't fetch robots.txt, assume allowed
        return True
    
    async def get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Get or create a semaphore for rate limiting a specific domain."""
        if domain not in self.domain_semaphores:
            # Allow up to 2 concurrent requests per domain
            self.domain_semaphores[domain] = asyncio.Semaphore(2)
        return self.domain_semaphores[domain]
    
    async def delay_if_needed(self, domain: str) -> None:
        """Implement rate limiting for a domain."""
        current_time = time.time()
        
        if domain in self.domain_last_request:
            elapsed = current_time - self.domain_last_request[domain]
            if elapsed < self.min_request_interval:
                delay = self.min_request_interval - elapsed
                logger.debug(f"Rate limiting: Waiting {delay:.2f}s before next request to {domain}")
                await asyncio.sleep(delay)
        
        self.domain_last_request[domain] = time.time()
    
    async def fetch_sitemap(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Fetch and parse sitemap to discover pages."""
        urls = []
        
        # Parse the base URL to get the domain
        parsed_url = urlparse(base_url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        sitemap_candidates = [
            f"{domain}/sitemap.xml",
            f"{domain}/sitemap_index.xml",
            f"{domain}/sitemap/sitemap.xml"
        ]
        
        # Try to find robots.txt first
        robots_parser = await self.fetch_robots_txt(domain, session)
        if robots_parser and hasattr(robots_parser, 'sitemaps'):
            sitemap_candidates = robots_parser.sitemaps + sitemap_candidates
        
        # Try each potential sitemap URL
        for sitemap_url in sitemap_candidates:
            try:
                domain_semaphore = await self.get_domain_semaphore(domain)
                async with domain_semaphore:
                    await self.delay_if_needed(domain)
                    async with session.get(sitemap_url, timeout=self.timeout) as response:
                        if response.status == 200:
                            sitemap_content = await response.text()
                            
                            # Parse the XML
                            try:
                                root = ET.fromstring(sitemap_content)
                                # Handle sitemap index files
                                if root.tag.endswith('sitemapindex'):
                                    for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                                        loc = sitemap.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                                        if loc is not None and loc.text:
                                            sub_urls = await self.fetch_sitemap(loc.text, session)
                                            urls.extend(sub_urls)
                                # Handle regular sitemaps
                                else:
                                    for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                                        loc = url_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                                        if loc is not None and loc.text:
                                            urls.append(loc.text)
                                
                                logger.info(f"Sitemap found at {sitemap_url}: {len(urls)} URLs")
                                # If we found a valid sitemap, we can stop searching
                                if urls:
                                    break
                            except ET.ParseError as e:
                                logger.warning(f"Error parsing sitemap XML at {sitemap_url}: {e}")
            except Exception as e:
                logger.warning(f"Error fetching sitemap {sitemap_url}: {str(e)}")
        
        # Return unique URLs
        return list(set(urls))
    
    async def extract_schema_org_data(self, soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
        """Extract schema.org structured data from a page."""
        schema_data = []
        
        # Look for JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                schema_data.append(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parsing JSON-LD schema in {url}: {e}")
        
        # Look for microdata
        # This is a simplistic implementation that could be expanded
        items = soup.find_all(itemscope=True)
        for item in items:
            try:
                item_type = item.get('itemtype', '')
                if not item_type:
                    continue
                    
                props = {}
                for prop in item.find_all(itemprop=True):
                    prop_name = prop.get('itemprop', '')
                    
                    # Extract property value based on tag type
                    if prop.name == 'meta':
                        prop_value = prop.get('content', '')
                    elif prop.name == 'link':
                        prop_value = prop.get('href', '')
                    elif prop.name == 'time':
                        prop_value = prop.get('datetime', prop.text.strip())
                    elif prop.name == 'img':
                        prop_value = prop.get('src', '')
                    else:
                        prop_value = prop.text.strip()
                        
                    props[prop_name] = prop_value
                
                if props:  # Only add if we found properties
                    schema_data.append({
                        '@type': item_type,
                        **props
                    })
            except Exception as e:
                logger.warning(f"Error extracting microdata in {url}: {e}")
        
        return schema_data
    
    def compute_content_hash(self, content: str) -> str:
        """Compute a hash of the content for diffing."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def detect_content_changes(self, url: str, content_hash: str, content: str) -> Dict[str, Any]:
        """Detect changes in content since last crawl."""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        result = {
            "is_changed": True,
            "first_seen": datetime.now().isoformat(),
            "last_changed": datetime.now().isoformat(),
        }
        
        if url_hash in self.content_cache:
            cache_entry = self.content_cache[url_hash]
            
            # Check if content hash changed
            if cache_entry["content_hash"] == content_hash:
                result["is_changed"] = False
                result["first_seen"] = cache_entry["first_seen"]
                result["last_changed"] = cache_entry["last_changed"]
            else:
                # Content changed
                result["first_seen"] = cache_entry["first_seen"]
                
                # TODO: Implement more detailed diffing here if needed
        
        # Update cache
        self.content_cache[url_hash] = {
            "url": url,
            "content_hash": content_hash,
            "first_seen": result["first_seen"],
            "last_changed": result["last_changed"] if result["is_changed"] else result["last_changed"]
        }
        
        return result
    
    async def fetch_url(self, url: str, depth: int, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Fetch a URL and extract content."""
        # Parse URL to get domain for rate limiting
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check robots.txt
        if not await self.is_allowed_by_robots(url, session):
            logger.info(f"Skipping {url} (disallowed by robots.txt)")
            return {
                "url": url,
                "success": False,
                "error": "Disallowed by robots.txt"
            }
        
        # Remove URL fragment
        url, _ = urldefrag(url)
        
        # Use domain-specific semaphore for per-domain rate limiting
        domain_semaphore = await self.get_domain_semaphore(domain)
        
        # Use both global and domain-specific semaphores
        async with self.request_semaphore, domain_semaphore:
            # Apply rate limiting
            await self.delay_if_needed(domain)
            
            try:
                # Fetch the URL
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
                
                # Add conditional GET headers if we have cached this URL before
                url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
                if url_hash in self.content_cache:
                    cache_entry = self.content_cache[url_hash]
                    if "etag" in cache_entry:
                        headers["If-None-Match"] = cache_entry["etag"]
                    if "last_modified" in cache_entry:
                        headers["If-Modified-Since"] = cache_entry["last_modified"]
                
                async with session.get(url, headers=headers, timeout=self.timeout, 
                                      allow_redirects=True, raise_for_status=False) as response:
                    # Handle redirects
                    if response.history:
                        final_url = str(response.url)
                        logger.info(f"Redirected: {url} -> {final_url}")
                        url = final_url
                    
                    # Handle not modified (304)
                    if response.status == 304:
                        logger.info(f"Content not modified: {url}")
                        # Return cached data
                        if url_hash in self.content_cache:
                            return {
                                "url": url,
                                "success": True,
                                "status_code": 304,
                                "content_type": "text/html",  # Assuming HTML for cached content
                                "from_cache": True,
                                "depth": depth,
                                "title": self.content_cache[url_hash].get("title", ""),
                                "html": self.content_cache[url_hash].get("html", ""),
                                "text": self.content_cache[url_hash].get("text", ""),
                                "links": self.content_cache[url_hash].get("links", []),
                                "images": self.content_cache[url_hash].get("images", []),
                                "schema_data": self.content_cache[url_hash].get("schema_data", []),
                                "content_hash": self.content_cache[url_hash].get("content_hash", ""),
                                "change_data": {
                                    "is_changed": False,
                                    "first_seen": self.content_cache[url_hash].get("first_seen", ""),
                                    "last_changed": self.content_cache[url_hash].get("last_changed", "")
                                }
                            }
                    
                    # Check if response is successful
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        return {
                            "url": url,
                            "success": False,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}"
                        }
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not content_type.startswith('text/html'):
                        logger.info(f"Skipping non-HTML content: {url} ({content_type})")
                        return {
                            "url": url,
                            "success": False,
                            "status_code": response.status,
                            "content_type": content_type,
                            "error": f"Not HTML content: {content_type}"
                        }
                    
                    # Get ETag and Last-Modified headers for caching
                    etag = response.headers.get('ETag')
                    last_modified = response.headers.get('Last-Modified')
                    
                    # Limit response size to avoid memory issues
                    content_length = int(response.headers.get('Content-Length', '0'))
                    if content_length > self.max_file_size:
                        logger.warning(f"Skipping large file: {url} ({content_length} bytes)")
                        return {
                            "url": url,
                            "success": False,
                            "status_code": response.status,
                            "content_type": content_type,
                            "error": f"File too large: {content_length} bytes"
                        }
                    
                    # Read the content
                    html = await response.text()
                    
                    # Parse the HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract information
                    title = soup.title.text.strip() if soup.title else ""
                    
                    # Extract text content
                    paragraphs = [p.text.strip() for p in soup.find_all('p') if p.text.strip()]
                    text_content = "\n\n".join(paragraphs)
                    
                    # Extract links
                    links = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith('javascript:') or href.startswith('#'):
                            continue
                            
                        # Make relative URLs absolute
                        absolute_url = urljoin(url, href)
                        
                        # Skip mailto and tel links
                        if absolute_url.startswith(('mailto:', 'tel:')):
                            continue
                            
                        # Parse the URL to check if it's valid
                        try:
                            parsed = urlparse(absolute_url)
                            if not parsed.scheme or not parsed.netloc:
                                continue
                        except Exception:
                            continue
                            
                        # Check if we should follow external links
                        is_external = urlparse(absolute_url).netloc != parsed_url.netloc
                        if is_external and not self.follow_external_links:
                            continue
                            
                        links.append({
                            "url": absolute_url,
                            "text": a.text.strip(),
                            "is_external": is_external
                        })
                    
                    # Extract images if enabled
                    images = []
                    if self.extract_images:
                        for img in soup.find_all('img'):
                            src = img.get('src')
                            if not src:
                                continue
                                
                            # Make relative URLs absolute
                            absolute_src = urljoin(url, src)
                            
                            images.append({
                                "url": absolute_src,
                                "alt": img.get('alt', ''),
                                "title": img.get('title', ''),
                                "width": img.get('width', ''),
                                "height": img.get('height', '')
                            })
                    
                    # Extract schema.org data if enabled
                    schema_data = []
                    if self.extract_schema:
                        schema_data = await self.extract_schema_org_data(soup, url)
                    
                    # Compute content hash for diffing
                    content_hash = self.compute_content_hash(html)
                    
                    # Detect content changes
                    change_data = self.detect_content_changes(url, content_hash, html)
                    
                    # Update cache with ETag and Last-Modified
                    if url_hash in self.content_cache:
                        self.content_cache[url_hash]["etag"] = etag
                        self.content_cache[url_hash]["last_modified"] = last_modified
                        self.content_cache[url_hash]["title"] = title
                        self.content_cache[url_hash]["html"] = html
                        self.content_cache[url_hash]["text"] = text_content
                        self.content_cache[url_hash]["links"] = links
                        self.content_cache[url_hash]["images"] = images
                        self.content_cache[url_hash]["schema_data"] = schema_data
                    
                    return {
                        "url": url,
                        "success": True,
                        "status_code": response.status,
                        "content_type": content_type,
                        "depth": depth,
                        "title": title,
                        "html": html,
                        "text": text_content,
                        "links": links,
                        "images": images,
                        "schema_data": schema_data,
                        "content_hash": content_hash,
                        "change_data": change_data
                    }
            except aiohttp.ClientError as e:
                logger.error(f"Client error fetching {url}: {str(e)}")
                return {
                    "url": url,
                    "success": False,
                    "error": f"Client error: {str(e)}"
                }
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url}")
                return {
                    "url": url,
                    "success": False,
                    "error": "Timeout"
                }
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                return {
                    "url": url,
                    "success": False,
                    "error": str(e)
                }
    
    async def process_url(self, url: str, depth: int, session: aiohttp.ClientSession) -> None:
        """Process a URL: fetch it and enqueue any new links."""
        # Skip if we've already crawled this URL or reached max pages
        url, _ = urldefrag(url)  # Remove URL fragment
        if url in self.crawled_urls or len(self.crawled_urls) >= self.max_pages:
            return
            
        logger.info(f"Processing {url} (depth {depth})")
        
        # Mark as crawled immediately to avoid duplicates
        self.crawled_urls.add(url)
        
        # Fetch the URL
        result = await self.fetch_url(url, depth, session)
        
        # If successful, add to results and enqueue links
        if result.get("success", False):
            # Add to results
            self.results["pages"][url] = result
            self.results["metadata"]["total_pages"] += 1
            
            # If we have more depth, enqueue links
            if depth < self.max_depth:
                for link in result.get("links", []):
                    link_url = link["url"]
                    
                    # Check if we should crawl this URL
                    if link_url not in self.crawled_urls and link_url not in self.failed_urls:
                        if link.get("is_external", False) and not self.follow_external_links:
                            continue
                            
                        # Add to queue with incremented depth
                        self.url_queue.append((link_url, depth + 1))
        else:
            # Mark as failed
            self.failed_urls.add(url)
            self.results["metadata"]["failed_pages"] += 1
    
    async def crawl(self, start_url: str) -> Dict[str, Any]:
        """
        Crawl a website starting from the given URL.
        
        Args:
            start_url: The URL to start crawling from
            
        Returns:
            Dict containing the crawl results
        """
        # Check if the start URL is valid
        if not validators.url(start_url):
            raise ValueError(f"Invalid URL: {start_url}")
            
        # Initialize state
        self.crawled_urls = set()
        self.failed_urls = set()
        self.url_queue = [(start_url, 0)]  # (url, depth)
        self.results = {
            "pages": {},
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "total_pages": 0,
                "failed_pages": 0,
                "settings": {
                    "max_pages": self.max_pages,
                    "max_depth": self.max_depth,
                    "follow_external_links": self.follow_external_links,
                    "extract_images": self.extract_images,
                    "extract_schema": self.extract_schema,
                }
            }
        }
        
        # Configure HTTP session
        timeout = ClientTimeout(total=self.timeout)
        connector = TCPConnector(limit=self.max_concurrent_requests)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Try to discover pages via sitemap if enabled
            if self.sitemap_discovery:
                logger.info(f"Discovering pages via sitemap for {start_url}")
                sitemap_urls = await self.fetch_sitemap(start_url, session)
                
                # Add sitemap URLs to queue
                for sitemap_url in sitemap_urls:
                    if sitemap_url not in [u for u, _ in self.url_queue]:
                        self.url_queue.append((sitemap_url, 0))
                
                logger.info(f"Added {len(sitemap_urls)} URLs from sitemap")
                
            # Process URLs in a breadth-first manner until queue is empty
            # or we've reached max pages
            with tqdm.asyncio.tqdm(total=self.max_pages, desc="Crawling") as pbar:
                while self.url_queue and len(self.crawled_urls) < self.max_pages:
                    # Get the next batch of URLs to process
                    # (limited by our concurrency settings)
                    batch = []
                    while self.url_queue and len(batch) < self.max_concurrent_requests:
                        batch.append(self.url_queue.pop(0))
                    
                    # Process the batch concurrently
                    tasks = [self.process_url(url, depth, session) for url, depth in batch]
                    await asyncio.gather(*tasks)
                    
                    # Update progress bar
                    pbar.update(len(self.crawled_urls) - pbar.n)
        
        # Record end time
        self.results["metadata"]["end_time"] = datetime.now().isoformat()
        
        # Save content cache for future diffing
        if self.track_changes:
            self._save_content_cache()
        
        logger.info(f"Crawl completed: {len(self.crawled_urls)} pages crawled, "
                    f"{len(self.failed_urls)} failed")
                    
        return self.results
    
    def save_results(self, output_dir: str) -> str:
        """
        Save crawl results to the specified directory.
        
        Args:
            output_dir: Directory to save results
            
        Returns:
            Path to the saved results
        """
        # Create the output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save as JSON
        output_path = os.path.join(output_dir, "crawl_results.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
            
        # Save pages in requested formats
        if "markdown" in self.output_formats:
            markdown_dir = os.path.join(output_dir, "markdown")
            os.makedirs(markdown_dir, exist_ok=True)
            
            for url, page in self.results["pages"].items():
                if page.get("success", False):
                    filename = self._url_to_filename(url, "md")
                    filepath = os.path.join(markdown_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {page.get('title', 'Untitled')}\n\n")
                        f.write(f"URL: {url}\n\n")
                        f.write(markdownify(page.get('html', '')))
        
        if "html" in self.output_formats:
            html_dir = os.path.join(output_dir, "html")
            os.makedirs(html_dir, exist_ok=True)
            
            for url, page in self.results["pages"].items():
                if page.get("success", False):
                    filename = self._url_to_filename(url, "html")
                    filepath = os.path.join(html_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(page.get('html', ''))
        
        return output_path
    
    def _url_to_filename(self, url: str, ext: str) -> str:
        """Convert a URL to a safe filename."""
        # Remove protocol and domain
        parsed = urlparse(url)
        path = parsed.path
        
        # Handle root URL
        if not path or path == '/':
            return f"index.{ext}"
            
        # Remove leading and trailing slashes
        path = path.strip('/')
        
        # Replace slashes and other unsafe characters
        safe_name = re.sub(r'[^\w\-\.]', '_', path)
        
        # Add extension if not already present
        if not safe_name.endswith(f".{ext}"):
            safe_name = f"{safe_name}.{ext}"
            
        return safe_name

# Function for easier use
async def crawl_website(url: str, **kwargs) -> Dict[str, Any]:
    """
    Crawl a website and return the results.
    
    Args:
        url: The starting URL to crawl
        **kwargs: Additional arguments to pass to WebsiteCrawler
        
    Returns:
        Dict containing the crawl results
    """
    crawler = WebsiteCrawler(**kwargs)
    results = await crawler.crawl(url)
    return results
