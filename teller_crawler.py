#!/usr/bin/env python3
"""
Simple Web Crawler for Teller Website

This is a crawler specifically targeting the Teller website (https://weareteller.webflow.io/).
"""

import os
import re
import time
import json
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TellerCrawler:
    """A crawler for the Teller website."""
    
    def __init__(self, 
                 start_url: str,
                 output_dir: str = './teller_output',
                 max_pages: int = 50,
                 max_depth: int = 3):
        """Initialize the crawler with given parameters."""
        self.start_url = start_url
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.max_depth = max_depth
        
        # URLs for tracking
        self.crawled_urls = set()
        self.queue = []
        
        # Stats
        self.stats = {
            "pages_crawled": 0,
            "images_found": 0,
            "links_found": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'html'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    
    def save_stats(self):
        """Save the crawling statistics to a JSON file."""
        stats_dir = os.path.join(self.output_dir, 'stats')
        os.makedirs(stats_dir, exist_ok=True)
        
        stats_file = os.path.join(stats_dir, 'crawler_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"Stats saved to {stats_file}")
    
    def save_html(self, url: str, html: str):
        """Save the HTML content to a file."""
        filename = self.url_to_filename(url)
        filepath = os.path.join(self.output_dir, 'html', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Saved HTML for {url} to {filepath}")
    
    def url_to_filename(self, url: str) -> str:
        """Convert a URL to a safe filename."""
        # Parse the URL
        parsed = urlparse(url)
        
        # Remove scheme and domain
        path = parsed.path
        if not path or path == '/':
            path = 'index'
        else:
            path = path.strip('/')
        
        # Handle query parameters if present
        if parsed.query:
            # Replace special characters in query string
            safe_query = re.sub(r'[^\w\-\.]', '_', parsed.query)
            path = f"{path}_{safe_query}"
        
        # Replace invalid characters
        path = re.sub(r'[^\w\-\.]', '_', path)
        
        # Add extension
        if not path.endswith('.html'):
            path += '.html'
        
        return path
    
    def has_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs have the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc
    
    async def extract_links(self, url: str, html: str) -> list:
        """Extract links from HTML content."""
        links = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip anchors and javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Make URL absolute
            abs_url = urljoin(url, href)
            
            # Only follow links within the same domain
            if self.has_same_domain(url, abs_url):
                links.append(abs_url)
        
        return links
    
    async def extract_images(self, url: str, html: str) -> list:
        """Extract images from HTML content."""
        images = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all image tags
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            
            # Make URL absolute
            abs_url = urljoin(url, src)
            
            # Extract image info
            images.append({
                'url': abs_url,
                'alt': img_tag.get('alt', ''),
                'width': img_tag.get('width', ''),
                'height': img_tag.get('height', '')
            })
        
        # Also look for background images in CSS style attributes
        for elem in soup.select('[style*="background-image"]'):
            style = elem.get('style', '')
            matches = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
            for match in matches:
                abs_url = urljoin(url, match)
                images.append({
                    'url': abs_url,
                    'alt': 'Background image',
                    'width': '',
                    'height': ''
                })
        
        return images
    
    async def crawl_url(self, url: str, depth: int, session: aiohttp.ClientSession):
        """Crawl a specific URL and extract content."""
        if url in self.crawled_urls or depth > self.max_depth:
            return
        
        logger.info(f"Crawling {url} (depth: {depth})")
        
        try:
            # Some sites block bots, so use a common user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Fetch the URL with a timeout
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return
                
                html = await response.text()
                
                # Save the HTML content
                self.save_html(url, html)
                
                # Extract links and add to queue
                links = await self.extract_links(url, html)
                self.stats["links_found"] += len(links)
                
                for link in links:
                    if link not in self.crawled_urls and len(self.queue) + len(self.crawled_urls) < self.max_pages:
                        self.queue.append((link, depth + 1))
                
                # Extract images
                images = await self.extract_images(url, html)
                self.stats["images_found"] += len(images)
                
                # Mark this URL as crawled
                self.crawled_urls.add(url)
                self.stats["pages_crawled"] += 1
                
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
    
    async def run(self):
        """Run the crawler starting from the initial URL."""
        logger.info(f"Starting crawler at {self.start_url}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Start with the initial URL
        self.queue.append((self.start_url, 0))
        
        # Create an HTTP session
        async with aiohttp.ClientSession() as session:
            # Process the queue
            while self.queue and len(self.crawled_urls) < self.max_pages:
                # Get the next URL and depth
                url, depth = self.queue.pop(0)
                
                # Crawl the URL
                await self.crawl_url(url, depth, session)
                
                # Simple rate limiting
                await asyncio.sleep(1)
        
        # Set the end time
        self.stats["end_time"] = datetime.now().isoformat()
        
        # Save the final stats
        self.save_stats()
        
        logger.info(f"Crawling completed. Processed {len(self.crawled_urls)} pages.")
        logger.info(f"Found {self.stats['links_found']} links and {self.stats['images_found']} images.")

async def download_images(html_dir, images_dir):
    """Download images from the crawled pages."""
    # Create ImageDownloader class instance
    from image_downloader import ImageDownloader
    downloader = ImageDownloader(html_dir, images_dir)
    
    # Run the downloader
    await downloader.download_images()

async def main():
    # URL to crawl
    url = "https://weareteller.webflow.io/"
    
    # Create output directory
    output_dir = "./teller_output"
    
    # Create and run the crawler
    crawler = TellerCrawler(url, output_dir)
    await crawler.run()
    
    # Download images
    html_dir = os.path.join(output_dir, "html")
    images_dir = os.path.join(output_dir, "images")
    await download_images(html_dir, images_dir)
    
    print(f"\nCrawling and image download completed! Output saved to {output_dir}")
    print(f"Pages crawled: {crawler.stats['pages_crawled']}")
    print(f"Links found: {crawler.stats['links_found']}")
    print(f"Images found: {crawler.stats['images_found']}")
    print(f"\nTo view the results, run: python teller_viewer.py")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 