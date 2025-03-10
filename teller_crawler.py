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
import sys
import argparse

from src.utils import normalize_url, extract_domain, CrawlerStats, ResourceExtractor
from image_downloader import ImageDownloader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class TellerWebsiteCrawler:
    def __init__(self, base_url, output_dir="./teller_output", max_pages=50, max_depth=3, download_resources=True):
        self.base_url = base_url
        self.domain = extract_domain(base_url)
        self.output_dir = output_dir
        self.html_dir = os.path.join(output_dir, "html")
        self.css_dir = os.path.join(output_dir, "css")
        self.js_dir = os.path.join(output_dir, "js")
        self.fonts_dir = os.path.join(output_dir, "fonts")
        self.stats_dir = os.path.join(output_dir, "stats")
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.download_resources = download_resources
        self.visited_urls = set()
        self.stats = CrawlerStats()
        self.resource_extractor = ResourceExtractor(base_url, output_dir)
        
        # Create output directories
        os.makedirs(self.html_dir, exist_ok=True)
        os.makedirs(self.css_dir, exist_ok=True)
        os.makedirs(self.js_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)
        os.makedirs(self.stats_dir, exist_ok=True)
    
    async def crawl(self):
        """Start the crawling process."""
        logger.info(f"Starting crawler at {self.base_url}")
        logger.info(f"Output directory: {self.output_dir}")
        
        async with aiohttp.ClientSession() as session:
            await self.crawl_url(self.base_url, session, depth=0)
            
        # Save final stats
        self.save_stats()
        logger.info(f"Crawling completed. Processed {self.stats.pages_crawled} pages.")
        logger.info(f"Found {self.stats.links_found} links and {self.stats.images_found} images.")
        
        return self.stats
        
    async def crawl_url(self, url, session, depth=0):
        """Crawl a specific URL and its links."""
        if url in self.visited_urls or len(self.visited_urls) >= self.max_pages or depth > self.max_depth:
            return
            
        self.visited_urls.add(url)
        logger.info(f"Crawling {url} (depth: {depth})")
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get {url}: HTTP {response.status}")
                    return
                html_content = await response.text()
                
            # Extract and download resources
            resources = {}
            if self.download_resources:
                resources = await self.download_resources_from_page(html_content, url, session)
                html_content = self.modify_html_for_local_resources(html_content, url, resources)
                
            # Save the HTML content
            file_path = self.get_file_path(url)
            self.save_html(html_content, file_path)
            self.stats.increment_page_crawled()
            
            # Extract and process links
            links = self.extract_links(html_content, url)
            
            # Extract images for statistics
            images = self.extract_images(html_content, url)
            
            # Process the next level of links
            for link in links:
                if self.should_crawl(link):
                    await self.crawl_url(link, session, depth + 1)
                    
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            
    async def download_resources_from_page(self, html_content, page_url, session):
        """Extract and download all resources from a page."""
        stylesheets = self.resource_extractor.extract_stylesheets(html_content, page_url)
        scripts = self.resource_extractor.extract_scripts(html_content, page_url)
        
        # Download CSS files
        css_downloads = []
        css_local_paths = {}
        for css_url in stylesheets:
            local_path = self.resource_extractor.get_local_path(css_url, 'css')
            if local_path:
                css_downloads.append(self.resource_extractor.download_resource(css_url, local_path, session))
                css_local_paths[css_url] = local_path
                
        # Download JS files
        js_downloads = []
        for js_url in scripts:
            local_path = self.resource_extractor.get_local_path(js_url, 'js')
            if local_path:
                js_downloads.append(self.resource_extractor.download_resource(js_url, local_path, session))
                
        # Wait for all downloads to complete
        all_downloads = css_downloads + js_downloads
        if all_downloads:
            results = await asyncio.gather(*all_downloads, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Download error: {result}")
                else:
                    success, url, bytes_downloaded = result
                    if success:
                        self.stats.increment_resource_downloaded()
                        self.stats.add_bytes_downloaded(bytes_downloaded)
        
        # Process CSS files to extract and download fonts
        fonts = []
        for css_url, css_local_path in css_local_paths.items():
            font_urls, font_results = await self.resource_extractor.process_css_for_fonts(css_url, css_local_path, session)
            fonts.extend(font_urls)
            
            # Update stats for downloaded fonts
            for result in font_results:
                if not isinstance(result, Exception) and result[0]:  # success
                    self.stats.increment_resource_downloaded()
                    self.stats.add_bytes_downloaded(result[2])  # bytes_downloaded
                    
        return {
            'stylesheets': stylesheets,
            'scripts': scripts,
            'fonts': fonts
        }
            
    def modify_html_for_local_resources(self, html_content, page_url, resources):
        """Modify HTML to use local versions of resources."""
        import re
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Update stylesheet links
        for link in soup.find_all('link', rel='stylesheet'):
            if 'href' in link.attrs:
                css_url = normalize_url(link['href'], page_url)
                if css_url and css_url in resources['stylesheets']:
                    local_path = self.resource_extractor.get_local_path(css_url, 'css')
                    if local_path:
                        relative_path = os.path.relpath(local_path, self.output_dir)
                        link['href'] = f"/{relative_path}"
                        
        # Update script sources
        for script in soup.find_all('script', src=True):
            js_url = normalize_url(script['src'], page_url)
            if js_url and js_url in resources['scripts']:
                local_path = self.resource_extractor.get_local_path(js_url, 'js')
                if local_path:
                    relative_path = os.path.relpath(local_path, self.output_dir)
                    script['src'] = f"/{relative_path}"
                    
        # Find and update inline styles that might reference external resources
        for style in soup.find_all('style'):
            css_content = style.string
            if css_content:
                # Replace font URLs
                for font_url in resources.get('fonts', []):
                    local_path = self.resource_extractor.get_local_path(font_url, 'font')
                    if local_path:
                        relative_path = os.path.relpath(local_path, self.output_dir)
                        # Escape special characters in the URL for regex
                        font_url_escaped = re.escape(font_url)
                        # Replace the URL in the CSS content
                        css_content = re.sub(
                            r'url\([\'"]?' + font_url_escaped + r'[\'"]?\)',
                            f'url("/{relative_path}")',
                            css_content
                        )
                style.string = css_content
                
        return str(soup)
            
    def extract_links(self, html_content, base_url):
        """Extract all links from the HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = normalize_url(href, base_url)
            if absolute_url:
                links.append(absolute_url)
                self.stats.increment_link_found()
                
        return links
        
    def extract_images(self, html_content, base_url):
        """Extract all image URLs from the HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []
        
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            absolute_url = normalize_url(src, base_url)
            if absolute_url:
                images.append(absolute_url)
                self.stats.increment_image_found()
                
        return images
        
    def should_crawl(self, url):
        """Determine if a URL should be crawled."""
        parsed_url = urlparse(url)
        return parsed_url.netloc == self.domain
        
    def get_file_path(self, url):
        """Generate a file path for a URL."""
        parsed = urlparse(url)
        path = parsed.path
        
        if not path or path == '/':
            filename = 'index.html'
        else:
            # Clean up path to create a valid filename
            path = path.strip('/')
            path = path.replace('/', '_')
            filename = f"{path}.html"
            
        return os.path.join(self.html_dir, filename)
        
    def save_html(self, html_content, file_path):
        """Save HTML content to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Saved HTML for {file_path}")
        except Exception as e:
            logger.error(f"Error saving HTML: {e}")
            
    def save_stats(self):
        """Save crawling statistics to a JSON file."""
        stats_file = os.path.join(self.stats_dir, "crawler_stats.json")
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats.to_dict(), f, indent=2)
            logger.info(f"Stats saved to {stats_file}")
        except Exception as e:
            logger.error(f"Error saving stats: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Teller website crawler")
    parser.add_argument("--url", default="https://weareteller.webflow.io/", help="URL to crawl")
    parser.add_argument("--output-dir", default="./teller_output", help="Output directory")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum number of pages to crawl")
    parser.add_argument("--max-depth", type=int, default=2, help="Maximum crawl depth")
    parser.add_argument("--no-resources", action="store_false", dest="download_resources", help="Don't download CSS/JS resources")
    
    args = parser.parse_args()
    
    crawler = TellerWebsiteCrawler(
        args.url,
        output_dir=args.output_dir,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        download_resources=args.download_resources
    )
    
    await crawler.crawl()
    
    # Download images
    downloader = ImageDownloader(args.output_dir)
    await downloader.run()
    
    print(f"Crawling and image download completed! Output saved to {args.output_dir}")
    print(f"Pages crawled: {crawler.stats.pages_crawled}")
    print(f"Links found: {crawler.stats.links_found}")
    print(f"Images found: {crawler.stats.images_found}")
    print(f"To view the results, run: python teller_viewer.py")
    
if __name__ == "__main__":
    asyncio.run(main()) 