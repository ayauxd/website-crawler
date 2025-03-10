#!/usr/bin/env python3
"""
Web Scraping Tool - Feature Demonstration

This script demonstrates the enhanced features of the web scraping tool,
including caching, rate limiting, sitemap support, and more.
"""
import os
import asyncio
import argparse
import logging
from datetime import datetime

from src.crawler import WebsiteCrawler
from src.renderer import JavaScriptRenderer, render_with_playwright
from src.utils import CrawlerStats, CrawlerDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("demo_scraper.log")
    ]
)
logger = logging.getLogger(__name__)

async def run_demo(url: str, output_dir: str, js_rendering: bool = False, dashboard: bool = True):
    """
    Run a demonstration of the web scraping tool.
    
    Args:
        url: The URL to scrape
        output_dir: Directory to save output
        js_rendering: Whether to use JavaScript rendering
        dashboard: Whether to show the dashboard
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create cache directory
    cache_dir = os.path.join(output_dir, '.cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create screenshot directory if using JS rendering
    screenshot_dir = None
    if js_rendering:
        screenshot_dir = os.path.join(output_dir, 'screenshots')
        os.makedirs(screenshot_dir, exist_ok=True)
    
    # Set up crawler settings
    crawler_settings = {
        'max_pages': 20,
        'max_depth': 2,
        'respect_robots_txt': True,
        'rate_limit': 1.0,  # 1 second between requests
        'user_agent': 'WebScraperDemo/1.0',
        'output_formats': ['html', 'markdown', 'json'],
        'follow_external_links': False,
        'timeout': 30,
        'extract_images': True,
        'extract_schema': True,
        'cache_dir': cache_dir,
        'track_changes': True,
        'sitemap_discovery': True,
        'max_concurrent_requests': 3
    }
    
    # Create stats tracker
    stats = CrawlerStats()
    
    # Start dashboard if requested
    dashboard_instance = None
    if dashboard:
        dashboard_instance = CrawlerDashboard(stats, update_interval=1)
        dashboard_instance.start()
    
    try:
        print(f"\n{'=' * 50}")
        print(f"Web Scraping Demo - {url}")
        print(f"{'=' * 50}")
        print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output directory: {output_dir}")
        print(f"JavaScript rendering: {'Enabled' if js_rendering else 'Disabled'}")
        print(f"Dashboard: {'Enabled' if dashboard else 'Disabled'}")
        print(f"{'=' * 50}\n")
        
        # Create crawler instance
        crawler = WebsiteCrawler(**crawler_settings)
        
        # Perform the crawl
        if js_rendering:
            print("Using JavaScript rendering for initial page")
            
            # Configure renderer
            renderer_settings = {
                'browser_type': 'chromium',
                'headless': True,
                'wait_strategies': ['networkidle', 'load', 'visible'],
                'screenshot_dir': screenshot_dir,
                'timeout': 30000,  # 30 seconds
                'max_retries': 2
            }
            
            # First render the page with JavaScript
            print(f"Rendering initial page: {url}")
            async with JavaScriptRenderer(**renderer_settings) as renderer:
                initial_render = await renderer.render_page(url)
                
                if initial_render['success']:
                    print("Initial page rendered successfully")
                    if screenshot_dir:
                        print(f"Screenshot saved (if available): {initial_render.get('screenshot', 'N/A')}")
                    
                    # Use the crawler with the rendered content
                    print("Starting crawl...")
                    result = await crawler.crawl(url)
                else:
                    print(f"Failed to render page: {initial_render.get('error', 'Unknown error')}")
                    return
        else:
            print("Using standard crawling (no JavaScript rendering)")
            print("Starting crawl...")
            result = await crawler.crawl(url)
        
        # Save results
        output_path = crawler.save_results(output_dir)
        
        # Display summary
        print(f"\n{'=' * 50}")
        print("Crawl Summary")
        print(f"{'=' * 50}")
        print(f"Pages crawled: {result['metadata']['total_pages']}")
        print(f"Failed pages: {result['metadata']['failed_pages']}")
        print(f"Results saved to: {output_path}")
        
        # Save stats
        if stats:
            stats_path = os.path.join(output_dir, "crawl_stats.json")
            stats.save_stats(stats_path)
            print(f"Detailed statistics saved to: {stats_path}")
        
        print(f"{'=' * 50}")
        print("Demo completed successfully!")
        print(f"{'=' * 50}\n")
    
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        logger.exception("Error during demo")
        print(f"\nDemo failed: {str(e)}")
    finally:
        # Stop dashboard if running
        if dashboard_instance:
            dashboard_instance.stop()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Web Scraping Tool Demo")
    parser.add_argument("--url", default="https://news.ycombinator.com", 
                      help="URL to scrape (default: https://news.ycombinator.com)")
    parser.add_argument("--output", "-o", default="./demo_output",
                      help="Output directory (default: ./demo_output)")
    parser.add_argument("--js", "-j", action="store_true",
                      help="Enable JavaScript rendering")
    parser.add_argument("--no-dashboard", action="store_true",
                      help="Disable the dashboard")
    
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    await run_demo(
        url=args.url,
        output_dir=args.output,
        js_rendering=args.js,
        dashboard=not args.no_dashboard
    )

if __name__ == "__main__":
    asyncio.run(main()) 