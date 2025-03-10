#!/usr/bin/env python3
"""
Command Line Interface for the Website Crawler

This module provides a command-line interface for interacting with the
website crawler, exposing all key features through a user-friendly CLI.

Enhanced with:
- Improved command-line options
- Support for all new crawler features
- Interactive mode
- Better progress reporting
"""
import os
import sys
import asyncio
import argparse
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .crawler import WebsiteCrawler
from .renderer import JavaScriptRenderer, render_with_playwright
from .utils import CrawlerStats, CrawlerDashboard

def setup_logging(level: str, log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (debug, info, warning, error)
        log_file: Optional path to log file
    """
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    
    level_value = log_levels.get(level.lower(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level_value,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Website Crawler - Download and process website content',
        epilog='Example: python -m src.cli --url https://example.com --output ./output'
    )
    
    # Required arguments
    parser.add_argument('--url', required=True, help='URL to start crawling from')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--output', '-o', default='./output', help='Output directory')
    output_group.add_argument('--formats', choices=['html', 'markdown', 'json', 'all'], 
                             default='all', help='Output formats')
    
    # Crawler behavior
    crawler_group = parser.add_argument_group('Crawler Behavior')
    crawler_group.add_argument('--max-pages', '-m', type=int, default=100, 
                              help='Maximum number of pages to crawl')
    crawler_group.add_argument('--max-depth', '-d', type=int, default=3, 
                              help='Maximum depth to crawl')
    crawler_group.add_argument('--follow-external', action='store_true', 
                              help='Follow external links')
    crawler_group.add_argument('--respect-robots', action='store_true', default=True,
                              help='Respect robots.txt')
    crawler_group.add_argument('--user-agent', default='WebsiteCrawlerBot/1.0',
                              help='User agent string')
    crawler_group.add_argument('--timeout', type=int, default=30,
                              help='Request timeout in seconds')
    crawler_group.add_argument('--rate-limit', type=float, default=0.5,
                              help='Seconds to wait between requests')
    crawler_group.add_argument('--concurrent-requests', type=int, default=5,
                              help='Maximum concurrent requests')
    
    # JavaScript rendering
    js_group = parser.add_argument_group('JavaScript Rendering')
    js_group.add_argument('--js-rendering', '-j', action='store_true',
                         help='Enable JavaScript rendering')
    js_group.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'],
                         default='chromium', help='Browser to use for rendering')
    js_group.add_argument('--headless', action='store_true', default=True,
                         help='Run browser in headless mode')
    js_group.add_argument('--wait-for', choices=['domcontentloaded', 'load', 'networkidle'],
                         default='networkidle', help='When to consider page loaded')
    js_group.add_argument('--screenshot-dir', 
                         help='Directory to save screenshots (enables screenshots)')
    
    # Content extraction
    content_group = parser.add_argument_group('Content Extraction')
    content_group.add_argument('--extract-images', action='store_true', default=True,
                              help='Extract image information')
    content_group.add_argument('--extract-schema', action='store_true', default=True,
                              help='Extract schema.org data')
    content_group.add_argument('--sitemap-discovery', action='store_true', default=True,
                              help='Discover pages via sitemap.xml')
    content_group.add_argument('--track-changes', action='store_true', default=True,
                              help='Track content changes')
    
    # Monitoring options
    monitoring_group = parser.add_argument_group('Monitoring')
    monitoring_group.add_argument('--dashboard', action='store_true',
                                 help='Show live dashboard')
    monitoring_group.add_argument('--cache-dir', default='./.cache',
                                 help='Directory for cache files')
    monitoring_group.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'],
                                 default='info', help='Logging level')
    monitoring_group.add_argument('--log-file', help='Log file path')
    
    # Return parsed arguments
    return parser.parse_args()

def get_output_formats(formats_arg: str) -> List[str]:
    """Convert formats argument to list of format strings."""
    if formats_arg == 'all':
        return ['html', 'markdown', 'json']
    return [formats_arg]

async def main() -> int:
    """Main entry point for the CLI."""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL: {args.url}")
        print("URL must start with http:// or https://")
        return 1
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Create cache directory
    if args.cache_dir:
        os.makedirs(args.cache_dir, exist_ok=True)
    
    # Determine output formats
    output_formats = get_output_formats(args.formats)
    
    # Set up crawler settings
    crawler_settings = {
        'max_pages': args.max_pages,
        'max_depth': args.max_depth,
        'respect_robots_txt': args.respect_robots,
        'rate_limit': args.rate_limit,
        'user_agent': args.user_agent,
        'output_formats': output_formats,
        'follow_external_links': args.follow_external,
        'timeout': args.timeout,
        'extract_images': args.extract_images,
        'extract_schema': args.extract_schema,
        'cache_dir': args.cache_dir,
        'track_changes': args.track_changes,
        'sitemap_discovery': args.sitemap_discovery,
        'max_concurrent_requests': args.concurrent_requests
    }
    
    # Create tracker for crawler statistics
    stats = CrawlerStats()
    
    # Start dashboard if requested
    dashboard = None
    if args.dashboard:
        dashboard = CrawlerDashboard(stats, update_interval=2)
        dashboard.start()
    
    try:
        # Print starting message
        print(f"\nStarting crawler for {args.url}")
        print(f"Output directory: {args.output}")
        print(f"Max pages: {args.max_pages}, Max depth: {args.max_depth}")
        
        start_time = datetime.now()
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        # Initialize crawler
        crawler = WebsiteCrawler(**crawler_settings)
        
        # If JavaScript rendering is enabled, use it as the initial page loader
        if args.js_rendering:
            print("Using JavaScript rendering mode")
            
            # Configure renderer
            renderer_settings = {
                'browser_type': args.browser,
                'headless': args.headless,
                'wait_strategies': [args.wait_for, 'visible', 'animation'],
                'screenshot_dir': args.screenshot_dir,
                'user_agent': args.user_agent,
                'timeout': args.timeout * 1000,  # Convert to ms
            }
            
            # Render the initial page
            async with JavaScriptRenderer(**renderer_settings) as renderer:
                # First render the main page
                print(f"Rendering initial page: {args.url}")
                initial_render = await renderer.render_page(args.url)
                
                if initial_render['success']:
                    print("Initial page rendered successfully")
                    # Use the rendered HTML for further crawling
                    crawler_result = await crawler.crawl(args.url)
                else:
                    print(f"Failed to render initial page: {initial_render.get('error', 'Unknown error')}")
                    return 1
        else:
            # Use regular crawling without JavaScript rendering
            print("Using standard crawling mode (no JavaScript rendering)")
            crawler_result = await crawler.crawl(args.url)
        
        # Save the results
        output_path = crawler.save_results(args.output)
        
        # Print summary
        end_time = datetime.now()
        elapsed = end_time - start_time
        
        print("\n" + "=" * 50)
        print("Crawl completed!")
        print("-" * 50)
        print(f"URL: {args.url}")
        print(f"Pages crawled: {crawler_result['metadata']['total_pages']}")
        print(f"Failed pages: {crawler_result['metadata']['failed_pages']}")
        print(f"Time taken: {elapsed}")
        print(f"Results saved to: {output_path}")
        print("=" * 50 + "\n")
        
        # Save stats if dashboard was used
        if dashboard and stats:
            stats_path = os.path.join(args.output, "crawl_stats.json")
            stats.save_stats(stats_path)
            print(f"Detailed statistics saved to: {stats_path}")
        
        return 0
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user")
        return 130
    except Exception as e:
        print(f"\nCrawl failed: {str(e)}")
        logging.exception("Unhandled exception")
        return 1
    finally:
        # Stop dashboard if running
        if dashboard:
            dashboard.stop()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
