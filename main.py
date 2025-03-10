#!/usr/bin/env python3
"""
Website Crawler - Main Entry Point

This script serves as the main entry point for the website crawler application.
"""
import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any, List

from src.crawler import WebsiteCrawler
from src.renderer import JavaScriptRenderer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def crawl_with_js_rendering(url: str, output_dir: str, **kwargs) -> Dict[str, Any]:
    """
    Crawl a website with JavaScript rendering support.
    
    Args:
        url: The starting URL to crawl
        output_dir: Directory to save results
        **kwargs: Additional crawler settings
        
    Returns:
        Dict containing the crawl results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize crawler with default settings
    crawler_settings = {
        'max_pages': 100,
        'max_depth': 5,
        'respect_robots_txt': True,
        'rate_limit': 0.5,
        'user_agent': "WebsiteCrawlerBot/1.0",
        'output_formats': ["markdown", "html"],
        'follow_external_links': False,
        'timeout': 30,
        'extract_images': True,
    }
    crawler_settings.update(kwargs)
    
    crawler = WebsiteCrawler(**crawler_settings)
    
    try:
        # Run the crawler
        logger.info(f"Starting crawl of {url}")
        results = await crawler.crawl(url)
        
        # Save results
        output_path = crawler.save_results(output_dir)
        
        # Print summary
        logger.info(f"Crawl completed: {len(results['pages'])} pages crawled")
        logger.info(f"Results saved to: {output_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during crawl: {str(e)}")
        raise

async def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Website Crawler')
    parser.add_argument('url', help='The URL to crawl')
    parser.add_argument('--output-dir', '-o', default='./output', help='Directory to save output')
    parser.add_argument('--max-pages', '-m', type=int, default=100, help='Maximum number of pages to crawl')
    parser.add_argument('--js-rendering', '-j', action='store_true', help='Enable JavaScript rendering')
    
    args = parser.parse_args()
    
    try:
        if args.js_rendering:
            logger.info("Using JavaScript rendering mode")
            # In JS rendering mode, we use both the headless browser and regular crawler
            async with JavaScriptRenderer() as renderer:
                # First render the main page
                initial_render = await renderer.render_page(args.url)
                
                if initial_render['success']:
                    logger.info(f"Successfully rendered {args.url}")
                    # Now use the crawler with the rendered content
                    results = await crawl_with_js_rendering(
                        args.url, 
                        args.output_dir,
                        max_pages=args.max_pages
                    )
                else:
                    logger.error(f"Failed to render {args.url}: {initial_render.get('error', 'Unknown error')}")
                    sys.exit(1)
        else:
            # Regular crawling without JavaScript rendering
            results = await crawl_with_js_rendering(
                args.url, 
                args.output_dir,
                max_pages=args.max_pages
            )
            
        print(f"\nCrawl of {args.url} completed successfully.")
        print(f"Pages crawled: {len(results['pages'])}")
        print(f"Results saved to: {args.output_dir}")
        
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nCrawl failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
