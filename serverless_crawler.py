import json
import os
import time
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
import uuid
from src.utils import CrawlerStats
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServerlessCrawler:
    """
    A crawler designed to work in serverless environments with timeout constraints.
    This crawler is designed to be called multiple times, processing a batch of URLs each time.
    """
    
    def __init__(self, base_url, job_id=None, output_dir=None, max_pages=100, max_depth=3):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.job_id = job_id or str(uuid.uuid4())
        self.output_dir = output_dir or f"output/{self.job_id}"
        self.max_pages = max_pages
        self.max_depth = max_depth
        
        # Set up directories
        self.html_dir = os.path.join(self.output_dir, "html")
        self.css_dir = os.path.join(self.output_dir, "css")
        self.js_dir = os.path.join(self.output_dir, "js")
        self.images_dir = os.path.join(self.output_dir, "images")
        self.fonts_dir = os.path.join(self.output_dir, "fonts")
        self.stats_file = os.path.join(self.output_dir, "stats.json")
        self.state_file = os.path.join(self.output_dir, "state.json")
        
        self._ensure_directories()
        
        # Initialize or load state
        self.state = self._load_state() or {
            "job_id": self.job_id,
            "url": base_url,
            "start_time": datetime.now().isoformat(),
            "status": "initialized",
            "queue": [base_url],
            "visited": set(),
            "in_progress": set(),
            "links_found": set(),
            "pages_crawled": 0,
            "resources_downloaded": {
                "css": 0,
                "js": 0,
                "images": 0,
                "fonts": 0
            },
            "errors": [],
            "last_run": None
        }
        
        # Convert sets back from lists in loaded state
        if isinstance(self.state["visited"], list):
            self.state["visited"] = set(self.state["visited"])
        if isinstance(self.state["in_progress"], list):
            self.state["in_progress"] = set(self.state["in_progress"])
        if isinstance(self.state["links_found"], list):
            self.state["links_found"] = set(self.state["links_found"])
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for directory in [self.output_dir, self.html_dir, self.css_dir, 
                          self.js_dir, self.images_dir, self.fonts_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def _load_state(self):
        """Load crawler state from state.json if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to load state file: {self.state_file}")
                return None
        return None
    
    def save_state(self):
        """Save the current state to the state file."""
        # Convert sets to lists for JSON serialization
        state_copy = self.state.copy()
        state_copy["visited"] = list(self.state["visited"])
        state_copy["in_progress"] = list(self.state["in_progress"])
        state_copy["links_found"] = list(self.state["links_found"])
        state_copy["last_run"] = datetime.now().isoformat()
        
        with open(self.state_file, 'w') as f:
            json.dump(state_copy, f, indent=2)
        
        # Also save stats
        self.save_stats()
    
    def save_stats(self):
        """Save the current stats to the stats file."""
        stats = {
            "job_id": self.job_id,
            "url": self.base_url,
            "start_time": self.state["start_time"],
            "last_run": datetime.now().isoformat(),
            "pages_crawled": self.state["pages_crawled"],
            "links_found": len(self.state["links_found"]),
            "resources": self.state["resources_downloaded"],
            "status": self.state["status"],
            "errors": len(self.state["errors"])
        }
        
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    async def process_batch(self, batch_size=5, timeout=8):
        """Process a batch of URLs from the queue, respecting the server's execution time."""
        if self.state["status"] == "completed":
            self.logger.info("Crawl already completed, nothing to process")
            return {"status": "completed", "message": "Crawl already completed"}
        
        self.state["status"] = "running"
        self.save_state()
        
        start_time = time.time()
        processed_count = 0
        batch = []
        
        # Get URLs from queue (up to batch_size)
        while len(batch) < batch_size and self.state["queue"]:
            url = self.state["queue"].pop(0)
            if url not in self.state["visited"] and url not in self.state["in_progress"]:
                batch.append(url)
                self.state["in_progress"].add(url)
        
        if not batch:
            # No more URLs to process
            self.state["status"] = "completed"
            self.save_state()
            return {"status": "completed", "message": "No more URLs to process"}
        
        self.logger.info(f"Processing batch of {len(batch)} URLs")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in batch:
                if self.state["pages_crawled"] >= self.max_pages:
                    self.logger.info(f"Reached max pages limit: {self.max_pages}")
                    break
                
                tasks.append(self.process_url(session, url))
            
            # Wait for all tasks or until timeout
            try:
                done, pending = await asyncio.wait(
                    tasks, 
                    timeout=timeout,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                # Process results from completed tasks
                for task in done:
                    try:
                        result = task.result()
                        if result:
                            processed_count += 1
                    except Exception as e:
                        self.state["errors"].append(str(e))
                        self.logger.error(f"Error processing URL: {e}")
                
                # Mark pending tasks for retry
                for task in pending:
                    task.cancel()
                    # The URLs for pending tasks will remain in in_progress
                    # and will be retried in the next batch
            
            except asyncio.TimeoutError:
                self.logger.warning("Timeout reached while processing batch")
        
        # Move any remaining in_progress URLs back to the queue
        remaining = list(self.state["in_progress"])
        for url in remaining:
            if url not in self.state["visited"] and url not in self.state["queue"]:
                self.state["queue"].append(url)
        self.state["in_progress"] = set()
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Processed {processed_count} URLs in {elapsed_time:.2f} seconds")
        
        # Check if we're done
        if not self.state["queue"] and not self.state["in_progress"]:
            self.state["status"] = "completed"
        
        self.save_state()
        
        return {
            "status": self.state["status"],
            "processed_count": processed_count,
            "remaining": len(self.state["queue"]),
            "total_processed": self.state["pages_crawled"],
            "elapsed_time": elapsed_time
        }
    
    async def process_url(self, session, url):
        """Process a single URL, downloading and parsing its content."""
        try:
            if url in self.state["visited"]:
                self.state["in_progress"].discard(url)
                return False
            
            self.logger.info(f"Processing URL: {url}")
            
            # Determine file paths
            filename = self._get_filename_from_url(url)
            output_path = os.path.join(self.html_dir, filename)
            
            # Download the page content
            async with session.get(url, timeout=5) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    self.state["errors"].append(f"HTTP {response.status} for {url}")
                    self.state["in_progress"].discard(url)
                    self.state["visited"].add(url)
                    return False
                
                content_type = response.headers.get('Content-Type', '')
                
                if 'text/html' in content_type:
                    # Process HTML content
                    html_content = await response.text()
                    
                    # Save the original HTML
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Parse HTML for links and resources
                    await self._process_html(url, html_content)
                    
                    # Update state
                    self.state["pages_crawled"] += 1
                    
                else:
                    # Handle non-HTML resources
                    await self._handle_resource(url, response, content_type)
                
                # Mark as processed
                self.state["in_progress"].discard(url)
                self.state["visited"].add(url)
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            self.state["errors"].append(f"Error processing {url}: {str(e)}")
            self.state["in_progress"].discard(url)
            self.state["visited"].add(url)
            return False
    
    async def _process_html(self, url, html_content):
        """Process HTML content to extract links and resources."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_links = set()
            
            # Process links (a tags)
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_url = urljoin(url, href)
                
                # Only follow links within the same domain
                if self._is_valid_url(absolute_url):
                    page_links.add(absolute_url)
                    self.state["links_found"].add(absolute_url)
                    
                    # Add to queue if we haven't visited or queued yet
                    if (absolute_url not in self.state["visited"] and 
                        absolute_url not in self.state["in_progress"] and
                        absolute_url not in self.state["queue"]):
                        self.state["queue"].append(absolute_url)
            
            # Process CSS, JS, images
            for tag, attr, resource_type in [
                ('link', 'href', 'css'),  # CSS files
                ('script', 'src', 'js'),  # JavaScript files
                ('img', 'src', 'images')  # Images
            ]:
                for element in soup.find_all(tag, **{attr: True}):
                    resource_url = element.get(attr)
                    if not resource_url or resource_url.startswith('data:'):
                        continue
                        
                    absolute_resource_url = urljoin(url, resource_url)
                    
                    # Add to queue with lower priority (append to end)
                    if (absolute_resource_url not in self.state["visited"] and 
                        absolute_resource_url not in self.state["in_progress"] and
                        absolute_resource_url not in self.state["queue"]):
                        self.state["queue"].append(absolute_resource_url)
            
            # Process font files in CSS
            for style_tag in soup.find_all('style'):
                style_content = style_tag.string
                if style_content:
                    # Extract font URLs from CSS using regex
                    font_urls = re.findall(r'url\([\'"]?(.*?\.(?:woff2?|ttf|eot))[\'"]?\)', style_content)
                    for font_url in font_urls:
                        absolute_font_url = urljoin(url, font_url)
                        if (absolute_font_url not in self.state["visited"] and 
                            absolute_font_url not in self.state["in_progress"] and
                            absolute_font_url not in self.state["queue"]):
                            self.state["queue"].append(absolute_font_url)
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML from {url}: {str(e)}")
            self.state["errors"].append(f"Error parsing HTML from {url}: {str(e)}")
    
    async def _handle_resource(self, url, response, content_type):
        """Handle downloading of non-HTML resources."""
        resource_type = 'other'
        output_dir = self.output_dir
        
        # Determine resource type and directory
        if 'text/css' in content_type or url.endswith('.css'):
            resource_type = 'css'
            output_dir = self.css_dir
        elif 'javascript' in content_type or url.endswith('.js'):
            resource_type = 'js'
            output_dir = self.js_dir
        elif 'image/' in content_type or any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']):
            resource_type = 'images'
            output_dir = self.images_dir
        elif any(url.endswith(ext) for ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']):
            resource_type = 'fonts'
            output_dir = self.fonts_dir
        
        # Generate filename
        filename = self._get_filename_from_url(url)
        output_path = os.path.join(output_dir, filename)
        
        # Download and save the resource
        content = await response.read()
        with open(output_path, 'wb') as f:
            f.write(content)
        
        # Update stats
        if resource_type in self.state["resources_downloaded"]:
            self.state["resources_downloaded"][resource_type] += 1
    
    def _get_filename_from_url(self, url):
        """Generate a filename from a URL, preserving extension."""
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Handle empty path (domain root)
        if not path or path == '/':
            return f"index_{parsed_url.netloc.replace('.', '_')}.html"
        
        # Extract the path and query
        filename = path.split('/')[-1]
        if not filename:
            filename = 'index.html'
        
        # Add query parameters to filename if they exist
        if parsed_url.query:
            query_hash = str(hash(parsed_url.query))[-8:]
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{query_hash}{ext}"
        
        # Ensure filename is valid
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # If no extension, add .html for pages
        if '.' not in filename:
            filename += '.html'
        
        return filename
    
    def _is_valid_url(self, url):
        """Check if a URL should be crawled (same domain and not a fragment)."""
        try:
            parsed_url = urlparse(url)
            
            # Skip fragment-only URLs
            if not parsed_url.netloc and not parsed_url.path and parsed_url.fragment:
                return False
            
            # Skip external domains
            if parsed_url.netloc and parsed_url.netloc != self.domain:
                return False
            
            # Skip certain file types
            if any(url.endswith(ext) for ext in ['.pdf', '.zip', '.exe', '.dmg', '.tar.gz']):
                return False
            
            return True
        except Exception:
            return False

async def run_crawler(base_url, job_id=None, output_dir=None, max_pages=100):
    """Run the crawler for a single batch of URLs."""
    crawler = ServerlessCrawler(base_url, job_id, output_dir, max_pages)
    results = await crawler.process_batch()
    return results

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python serverless_crawler.py <url> [job_id] [max_pages]")
        sys.exit(1)
    
    url = sys.argv[1]
    job_id = sys.argv[2] if len(sys.argv) > 2 else None
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(run_crawler(url, job_id, max_pages=max_pages))
    
    print(json.dumps(result, indent=2)) 