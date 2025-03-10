# Cut n Sew Web Crawler

![Cut n Sew Web Crawler Logo](static/images/logo.png)

A stylish, retro-themed web crawler that captures complete websites with all resources for offline viewing.

## Features

- 🕸️ Complete website crawling with depth and page limits
- 📄 HTML content preservation with proper structure
- 🎨 CSS stylesheets and designs capture
- 📜 JavaScript functionality preservation
- 🔤 Font files extraction and downloading
- 🖼️ Images and media files acquisition
- 👀 Interactive browsing interface with typewriter aesthetics
- 📊 Resource statistics and metrics
- 📦 Downloadable archives of crawled sites

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (optional)

### Installation

1. Clone the repository (or download it)

```bash
git clone https://github.com/ayauxd/website-crawler.git
cd website-crawler
```

2. Create a virtual environment

```bash
python -m venv .venv
```

3. Activate the virtual environment

On Windows:
```bash
.venv\Scripts\activate
```

On macOS/Linux:
```bash
source .venv/bin/activate
```

4. Install dependencies

```bash
pip install -r requirements.txt
```

### Running the Application

1. Start the application:

```bash
python web_interface_retro.py
```

2. Open your browser and navigate to:

```
http://localhost:5050
```

3. Enter the URL of a website you want to crawl, set your options, and click "Start Crawling"

## Deployment on Vercel

This application can be deployed to Vercel with minimal configuration.

1. Install Vercel CLI:

```bash
npm install -g vercel
```

2. Login to Vercel:

```bash
vercel login
```

3. Deploy the application:

```bash
vercel
```

4. For production deployment:

```bash
vercel --prod
```

## How It Works

Cut n Sew Web Crawler extracts a website's content by:

1. Crawling the site page by page, respecting depth and page limits
2. Extracting all linked resources (CSS, JavaScript, fonts, images) 
3. Downloading resources to a local directory structure
4. Modifying HTML to use local resource paths
5. Providing a retro typewriter-themed interface to browse the results

## Use Cases

- 🔄 Website archiving for preservation
- 🌐 Offline browsing capability
- 🚚 Website migration assistance
- 🎓 Web design study and analysis
- 🧪 Offline testing and site modifications

## Limitations

- Some websites block web crawlers through robots.txt
- JavaScript-rendered content may not be fully captured
- Dynamic content that loads through APIs may not be preserved
- CAPTCHAs and login-required sites cannot be fully crawled
- Very large websites may require significant disk space

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the artistry of tailors who craft perfect garments piece by piece
- Special Elite font by Astigmatic
- Built with Flask, BeautifulSoup, and Python async capabilities
