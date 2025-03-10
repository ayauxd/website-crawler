# Advanced Web Scraping Tool

A powerful web scraping tool for extracting content from websites with advanced features including JavaScript rendering, sitemaps, caching, and more.

## Features

### Core Capabilities
- **Full-site Crawling**: Crawl entire websites following links to a specified depth
- **JavaScript Rendering**: Process JavaScript-heavy websites using headless browsers
- **Sitemap Support**: Automatically discover pages through sitemap.xml files
- **Rate Limiting**: Respectful crawling with configurable delays between requests
- **Robots.txt Compliance**: Honor robots.txt directives to be a good web citizen

### Performance & Reliability
- **Caching System**: Cache HTTP responses and content to avoid redundant downloads
- **Content Diffing**: Track and detect changes in content over time
- **Concurrent Crawling**: Process multiple pages simultaneously with proper rate limiting
- **Retry Logic**: Automatic retry for failed requests with exponential backoff
- **Resource Optimization**: Intelligent resource allocation and cleanup

### Content Extraction
- **Multiple Output Formats**: Export content as HTML, Markdown, and JSON
- **Structured Data Extraction**: Extract schema.org data from websites
- **Image Extraction**: Identify and download images from pages
- **Text Processing**: Extract clean, readable text from HTML content

### Monitoring & Debugging
- **Live Dashboard**: Real-time monitoring of crawler progress and statistics
- **Detailed Logging**: Comprehensive logging of crawler activities
- **Screenshot Capture**: Take screenshots of rendered pages for debugging
- **Performance Metrics**: Track and report on performance and usage statistics

## Installation

### Prerequisites
- Python 3.9 or higher
- Required Python packages (see `requirements.txt`)
- Playwright (for JavaScript rendering)

### Install Dependencies
```bash
# Clone the repository
git clone https://github.com/yourusername/web-scraping-tool.git
cd web-scraping-tool

# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (if using JavaScript rendering)
python -m playwright install
```

## Quick Start

### Basic Usage
```bash
# Crawl a website with default settings
python main.py --url https://example.com --output ./output
```

### Use JavaScript Rendering
```bash
# Crawl with JavaScript rendering enabled
python main.py --url https://example.com --output ./output --js-rendering
```

### Enable Dashboard and Advanced Features
```bash
# Crawl with dashboard and other advanced features
python main.py --url https://example.com --output ./output --dashboard --sitemap-discovery --track-changes
```

### Run the Demo
```bash
# Run the demonstration script
python demo.py --url https://example.com --output ./demo_output --js
```

## Command Line Options

### Basic Options
- `--url URL`: The starting URL to crawl
- `--output PATH`: Directory to save output (default: ./output)
- `--max-pages N`: Maximum number of pages to crawl (default: 100)
- `--max-depth N`: Maximum link depth to follow (default: 3)

### Crawler Behavior
- `--follow-external`: Follow external links (default: False)
- `--respect-robots`: Respect robots.txt rules (default: True)
- `--rate-limit SECONDS`: Seconds between requests (default: 0.5)
- `--concurrent-requests N`: Maximum concurrent requests (default: 5)
- `--timeout SECONDS`: Request timeout in seconds (default: 30)

### JavaScript Rendering
- `--js-rendering`: Enable JavaScript rendering
- `--browser TYPE`: Browser to use (chromium, firefox, webkit)
- `--headless`: Run browser in headless mode (default: True)
- `--wait-for TYPE`: When to consider page loaded (domcontentloaded, load, networkidle)
- `--screenshot-dir PATH`: Directory to save screenshots

### Content Extraction
- `--formats TYPE`: Output formats (html, markdown, json, all)
- `--extract-images`: Extract image information (default: True)
- `--extract-schema`: Extract schema.org data (default: True)
- `--sitemap-discovery`: Discover pages via sitemap.xml (default: True)
- `--track-changes`: Track content changes (default: True)

### Monitoring
- `--dashboard`: Show live dashboard
- `--cache-dir PATH`: Directory for cache files (default: ./.cache)
- `--log-level LEVEL`: Logging level (debug, info, warning, error)
- `--log-file PATH`: Log file path

## API Usage

You can also use this tool as a library in your Python code:

```python
import asyncio
from src.crawler import WebsiteCrawler

async def crawl_example():
    # Configure crawler settings
    crawler = WebsiteCrawler(
        max_pages=20,
        max_depth=2,
        respect_robots_txt=True,
        extract_images=True,
        sitemap_discovery=True,
        cache_dir="./.cache"
    )
    
    # Perform the crawl
    results = await crawler.crawl("https://example.com")
    
    # Save the results
    crawler.save_results("./output")

# Run the crawler
asyncio.run(crawl_example())
```

## JavaScript Rendering Example

```python
import asyncio
from src.renderer import JavaScriptRenderer

async def render_example():
    async with JavaScriptRenderer(headless=True) as renderer:
        result = await renderer.render_page("https://example.com")
        print(f"Page title: {result['title']}")
        print(f"Found {len(result['links'])} links")

# Run the renderer
asyncio.run(render_example())
```

## Advanced Configuration

See the [Documentation](./docs/) for detailed information on advanced configuration options and customization.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
