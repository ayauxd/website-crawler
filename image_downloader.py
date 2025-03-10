#!/usr/bin/env python3
"""
Image Downloader for Mac Template Website

This script downloads images from the Mac template website based on the HTML files
that have already been crawled.
"""

import os
import re
import json
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImageDownloader:
    """Downloads images from HTML files."""
    
    def __init__(self, html_dir: str, output_dir: str):
        """Initialize the downloader with the HTML directory and output directory."""
        self.html_dir = html_dir
        self.output_dir = output_dir
        self.stats = {
            "images_found": 0,
            "images_downloaded": 0,
            "bytes_downloaded": 0
        }
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def get_html_files(self) -> list:
        """Get all HTML files in the HTML directory."""
        html_files = []
        for file in os.listdir(self.html_dir):
            if file.endswith('.html'):
                html_files.append(os.path.join(self.html_dir, file))
        return html_files
    
    def extract_images_from_html(self, html_file: str) -> list:
        """Extract image URLs from an HTML file."""
        images = []
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html = f.read()
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find base URL
                base_url = None
                base_tag = soup.find('base', href=True)
                if base_tag and base_tag['href']:
                    base_url = base_tag['href']
                else:
                    # Try to extract from file name or content
                    match = re.search(r'https?://[^"\'>\s]+', html)
                    if match:
                        base_url = match.group(0)
                
                if not base_url:
                    base_url = "https://mac-template.webflow.io/"
                
                # Find all images
                for img in soup.find_all('img', src=True):
                    src = img.get('src')
                    if src:
                        # Make URL absolute
                        if not src.startswith(('http://', 'https://')):
                            img_url = urljoin(base_url, src)
                        else:
                            img_url = src
                        
                        # Store image info
                        images.append({
                            'url': img_url,
                            'alt': img.get('alt', ''),
                            'filename': self.url_to_filename(img_url)
                        })
        except Exception as e:
            logger.error(f"Error extracting images from {html_file}: {str(e)}")
        
        return images
    
    def url_to_filename(self, url: str) -> str:
        """Convert a URL to a safe filename."""
        # Parse the URL
        parsed = urlparse(url)
        
        # Get the path and query
        path = parsed.path
        
        # Get the file name from the path
        filename = os.path.basename(path)
        
        # If no filename or it doesn't have an extension, use a hash of the URL
        if not filename or '.' not in filename:
            import hashlib
            filename = hashlib.md5(url.encode()).hexdigest() + '.jpg'
        
        # Make sure the filename is safe
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        return filename
    
    async def download_image(self, session: aiohttp.ClientSession, img_info: dict) -> bool:
        """Download an image."""
        url = img_info['url']
        filename = img_info['filename']
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    # Check content type to ensure it's an image
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"Skipping {url} - not an image (content-type: {content_type})")
                        return False
                    
                    # Get content
                    content = await response.read()
                    
                    # Save to file
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    # Update stats
                    self.stats["images_downloaded"] += 1
                    self.stats["bytes_downloaded"] += len(content)
                    
                    logger.info(f"Downloaded {url} to {filepath} ({len(content)} bytes)")
                    return True
                else:
                    logger.warning(f"Failed to download {url}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return False
    
    async def download_images(self):
        """Download all images from the HTML files."""
        # Get all HTML files
        html_files = self.get_html_files()
        logger.info(f"Found {len(html_files)} HTML files")
        
        # Extract images from HTML files
        all_images = []
        for html_file in html_files:
            images = self.extract_images_from_html(html_file)
            all_images.extend(images)
        
        # Remove duplicates (by URL)
        unique_images = {img['url']: img for img in all_images}.values()
        self.stats["images_found"] = len(unique_images)
        
        logger.info(f"Found {len(unique_images)} unique images to download")
        
        # Download images
        async with aiohttp.ClientSession() as session:
            tasks = []
            for img in unique_images:
                tasks.append(self.download_image(session, img))
            
            # Run downloads with a limit of 5 concurrent downloads
            semaphore = asyncio.Semaphore(5)
            
            async def download_with_semaphore(img):
                async with semaphore:
                    return await self.download_image(session, img)
            
            results = await asyncio.gather(*[download_with_semaphore(img) for img in unique_images])
        
        # Save stats
        self.save_stats()
        
        return self.stats
    
    def save_stats(self):
        """Save download statistics to a JSON file."""
        stats_dir = os.path.join(os.path.dirname(self.output_dir), 'stats')
        os.makedirs(stats_dir, exist_ok=True)
        
        stats_file = os.path.join(stats_dir, 'image_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"Stats saved to {stats_file}")

async def main():
    # Directories
    html_dir = "./mac_template_output/html"
    output_dir = "./mac_template_output/images"
    
    # Create and run the downloader
    downloader = ImageDownloader(html_dir, output_dir)
    stats = await downloader.download_images()
    
    print(f"\nImage download completed!")
    print(f"Images found: {stats['images_found']}")
    print(f"Images downloaded: {stats['images_downloaded']}")
    print(f"Total bytes downloaded: {stats['bytes_downloaded']} bytes ({stats['bytes_downloaded']/1024:.1f} KB)")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 