#!/usr/bin/env python3
"""
Image Downloader for Kimuto Engineering Website

This script downloads images from kimutoengineering.com and saves them to a local directory.
Enhanced with caching, retry logic, and configuration options.
"""
import os
import re
import asyncio
import aiohttp
import logging
import argparse
import json
import time
import hashlib
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("image_downloader.log")
    ]
)
logger = logging.getLogger(__name__)

# Default values
DEFAULT_BASE_URL = "https://kimutoengineering.com"
DEFAULT_OUTPUT_DIR = "kimuto-redesign/assets/images"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2  # seconds
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_CONCURRENT_DOWNLOADS = 5

class ImageDownloader:
    """Class for downloading images from a website with caching and retry logic."""
    
    def __init__(self, 
                 base_url: str,
                 output_dir: str,
                 cache_dir: str = DEFAULT_CACHE_DIR,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 retry_delay: int = DEFAULT_RETRY_DELAY,
                 timeout: int = DEFAULT_TIMEOUT,
                 concurrent_downloads: int = DEFAULT_CONCURRENT_DOWNLOADS,
                 user_agent: str = "ImageDownloaderBot/1.0"):
        """Initialize the image downloader with configuration."""
        self.base_url = base_url
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.concurrent_downloads = concurrent_downloads
        self.user_agent = user_agent
        
        # Ensure directories exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load cache if exists
        self.cache_file = os.path.join(cache_dir, "image_cache.json")
        self.cache = self._load_cache()
        
        # Stats
        self.stats = {
            "total_images_found": 0,
            "new_downloads": 0,
            "cached": 0,
            "failed": 0,
            "retries": 0
        }

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load the cache from disk if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading cache file: {e}. Starting with empty cache.")
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save the cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except IOError as e:
            logger.error(f"Error saving cache: {e}")
    
    async def download_image(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Download an image from a URL with caching and retry logic."""
        # Parse the URL to get the filename
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # Generate a cache key
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Check if already downloaded
        output_path = os.path.join(self.output_dir, filename)
        if os.path.exists(output_path):
            if url_hash in self.cache:
                logger.info(f"Image already exists (cached): {filename}")
                self.stats["cached"] += 1
                return filename
        
        # Try to download with retries
        for attempt in range(self.max_retries):
            try:
                headers = {"User-Agent": self.user_agent}
                
                # Add ETag from cache if available
                if url_hash in self.cache and "etag" in self.cache[url_hash]:
                    headers["If-None-Match"] = self.cache[url_hash]["etag"]
                
                # Add Last-Modified from cache if available
                if url_hash in self.cache and "last_modified" in self.cache[url_hash]:
                    headers["If-Modified-Since"] = self.cache[url_hash]["last_modified"]
                
                # Download the image
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    # Handle 304 Not Modified
                    if response.status == 304:
                        logger.info(f"Image not modified (304): {filename}")
                        self.stats["cached"] += 1
                        return filename
                    
                    # Handle successful response
                    if response.status == 200:
                        # Get cache headers
                        etag = response.headers.get("ETag")
                        last_modified = response.headers.get("Last-Modified")
                        
                        # Save the image
                        with open(output_path, 'wb') as f:
                            f.write(await response.read())
                        
                        # Update cache
                        self.cache[url_hash] = {
                            "url": url,
                            "filename": filename,
                            "downloaded_at": time.time(),
                            "etag": etag,
                            "last_modified": last_modified
                        }
                        
                        logger.info(f"Downloaded: {filename}")
                        self.stats["new_downloads"] += 1
                        return filename
                    else:
                        logger.warning(f"Failed to download {url}: HTTP {response.status} (Attempt {attempt+1}/{self.max_retries})")
                        
                        if attempt < self.max_retries - 1:
                            self.stats["retries"] += 1
                            await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
            except asyncio.TimeoutError:
                logger.warning(f"Timeout downloading {url} (Attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    self.stats["retries"] += 1
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Error downloading {url}: {str(e)} (Attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    self.stats["retries"] += 1
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # If all retries failed
        self.stats["failed"] += 1
        return None

    async def extract_image_urls_from_page(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """Extract all image URLs from a web page with retry logic."""
        image_urls = []
        
        for attempt in range(self.max_retries):
            try:
                headers = {"User-Agent": self.user_agent}
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find all image tags
                        for img in soup.find_all('img'):
                            src = img.get('src')
                            if src:
                                # Make relative URLs absolute
                                image_url = urljoin(url, src)
                                image_urls.append(image_url)
                        
                        logger.info(f"Found {len(image_urls)} images on {url}")
                        return image_urls
                    else:
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status} (Attempt {attempt+1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)} (Attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return []

    async def extract_page_urls(self, session: aiohttp.ClientSession, base_url: str) -> List[str]:
        """Extract all page URLs from the website with retry logic."""
        page_urls = [base_url]
        
        for attempt in range(self.max_retries):
            try:
                headers = {"User-Agent": self.user_agent}
                async with session.get(base_url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find all links
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            # Skip anchors, external links, and non-HTML files
                            if href.startswith('#') or href.startswith('http') and not href.startswith(self.base_url):
                                continue
                            if href.endswith('.pdf') or href.endswith('.jpg') or href.endswith('.png'):
                                continue
                            
                            # Make relative URLs absolute
                            page_url = urljoin(base_url, href)
                            if page_url not in page_urls and urlparse(page_url).netloc == urlparse(base_url).netloc:
                                page_urls.append(page_url)
                        
                        logger.info(f"Found {len(page_urls)} pages on the website")
                        return page_urls
                    else:
                        logger.warning(f"Failed to fetch {base_url}: HTTP {response.status} (Attempt {attempt+1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Error fetching {base_url}: {str(e)} (Attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return [base_url]

    async def download_all_images(self) -> Dict[str, Any]:
        """Main method to download all images from the website."""
        start_time = time.time()
        
        # Configure client session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        conn = aiohttp.TCPConnector(limit=self.concurrent_downloads)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
            # Extract all page URLs
            page_urls = await self.extract_page_urls(session, self.base_url)
            
            # Extract image URLs from each page
            all_image_urls = []
            for page_url in page_urls:
                image_urls = await self.extract_image_urls_from_page(session, page_url)
                all_image_urls.extend(image_urls)
            
            # Remove duplicates
            all_image_urls = list(set(all_image_urls))
            self.stats["total_images_found"] = len(all_image_urls)
            logger.info(f"Found {len(all_image_urls)} unique images across all pages")
            
            # Download all images with concurrency control
            semaphore = asyncio.Semaphore(self.concurrent_downloads)
            
            async def download_with_semaphore(url):
                async with semaphore:
                    return await self.download_image(session, url)
            
            # Download all images
            tasks = [download_with_semaphore(url) for url in all_image_urls]
            downloaded_files = await asyncio.gather(*tasks)
            
            # Count successful downloads
            successful = [f for f in downloaded_files if f]
            
            # Save cache
            self._save_cache()
            
            # Calculate time taken
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Update and return stats
            self.stats["successful_downloads"] = len(successful)
            self.stats["elapsed_time"] = elapsed
            
            logger.info(f"Downloaded {len(successful)} images to {self.output_dir}")
            logger.info(f"Time taken: {elapsed:.2f} seconds")
            logger.info(f"Stats: {self.stats}")
            
            return self.stats

async def main():
    """Parse command-line arguments and run the image downloader."""
    parser = argparse.ArgumentParser(description='Download images from a website with caching and retry logic.')
    parser.add_argument('--url', default=DEFAULT_BASE_URL, help=f'Base URL to start crawling (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR, help=f'Directory to save images (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--cache-dir', default=DEFAULT_CACHE_DIR, help=f'Directory to store cache (default: {DEFAULT_CACHE_DIR})')
    parser.add_argument('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retries (default: {DEFAULT_MAX_RETRIES})')
    parser.add_argument('--retry-delay', type=int, default=DEFAULT_RETRY_DELAY, help=f'Delay between retries in seconds (default: {DEFAULT_RETRY_DELAY})')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help=f'Request timeout in seconds (default: {DEFAULT_TIMEOUT})')
    parser.add_argument('--concurrent', type=int, default=DEFAULT_CONCURRENT_DOWNLOADS, help=f'Number of concurrent downloads (default: {DEFAULT_CONCURRENT_DOWNLOADS})')
    parser.add_argument('--user-agent', default="ImageDownloaderBot/1.0", help='User agent string to use for requests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run the downloader
    try:
        downloader = ImageDownloader(
            base_url=args.url,
            output_dir=args.output,
            cache_dir=args.cache_dir,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            timeout=args.timeout,
            concurrent_downloads=args.concurrent,
            user_agent=args.user_agent
        )
        
        stats = await downloader.download_all_images()
        
        print("\nDownload Summary:")
        print(f"- Total images found: {stats['total_images_found']}")
        print(f"- New downloads: {stats['new_downloads']}")
        print(f"- Retrieved from cache: {stats['cached']}")
        print(f"- Failed downloads: {stats['failed']}")
        print(f"- Retries performed: {stats['retries']}")
        print(f"- Time taken: {stats['elapsed_time']:.2f} seconds")
        
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 