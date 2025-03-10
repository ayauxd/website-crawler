# Crawlr - Web Archive Tool

Crawlr is a vintage-inspired web archiving tool that captures and preserves websites for offline viewing, analysis, and development. Its serverless-friendly architecture allows you to crawl websites and collect their HTML, CSS, JavaScript, images, and fonts in an organized and accessible format.

![Crawlr Screenshot](https://example.com/screenshot.png) <!-- Add a screenshot if available -->

## Features

- **Complete Website Archiving**: Crawls entire websites, capturing HTML, CSS, JavaScript, images, and fonts
- **Serverless Architecture**: Works within serverless platforms' constraints by processing sites in small batches
- **Retro Interface**: Easy-to-use interface with vintage typewriter aesthetics
- **Organized Output**: Creates a structured archive of web resources for easy browsing and reuse
- **Developer-Friendly**: Perfect for studying website designs, creating templates, or preserving online content

## Using Archived Files in Your IDE

After crawling a website, you can use the archived files in your development environment:

1. Browse to the completed archive in the Crawlr interface
2. Click on any file (HTML, CSS, JS, etc.) to view its contents
3. Copy the code directly or use the download options
4. Import into your IDE maintaining the same folder structure:
   - `html/` directory contains the HTML files
   - `css/` directory contains the stylesheets
   - `js/` directory contains JavaScript files
   - `images/` and `fonts/` contain media resources

This makes it easy to:
- Study how websites are built
- Create templates based on existing designs
- Modify and extend websites for your own projects
- Preserve content that might change or disappear

## Deployment to Vercel

### Quick Deployment

1. Install Vercel CLI:
   ```
   npm install -g vercel
   ```

2. Login to Vercel:
   ```
   vercel login
   ```

3. Deploy the application:
   ```
   vercel
   ```

4. Follow the prompts:
   - Set up and deploy: Yes
   - Which scope: Select your personal account
   - Link to existing project: No
   - Project name: crawlr (or your preferred name)
   - Directory: ./ (current directory)
   - Override settings: No

### Troubleshooting Vercel Deployment

If you encounter a 500 error with `FUNCTION_INVOCATION_FAILED`, check the following:

1. **Proper Handler**: Make sure `index.py` exists with a `handler` function that imports the Flask app.
2. **Vercel Configuration**: Check `vercel.json` to ensure it points to `index.py` as the source file.
3. **Environment Variables**: Make sure OUTPUT_DIR is set to `/tmp/crawler_output` in Vercel environment.
4. **Dependencies**: Ensure all required packages are in `requirements.txt` with specific versions.

## Project Structure

```
├── index.py               # Vercel entry point
├── serverless_crawler.py  # Core crawler implementation
├── serverless_api.py      # Flask API for web interface
├── static/                # Static assets
│   └── css/
│       └── retro.css      # Retro styling for the interface
├── templates/             # HTML templates
│   ├── index.html         # Main interface template
│   ├── archive.html       # Archive viewer template
│   └── error.html         # Error page template
├── vercel.json            # Vercel deployment configuration
└── requirements.txt       # Project dependencies
```

## Local Development

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/crawlr.git
   cd crawlr
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python serverless_api.py
   ```

4. Open your browser and navigate to `http://127.0.0.1:5050` to access the interface.

## How It Works

The crawler operates with Vercel's serverless architecture limitations in mind:

1. **Batched Processing**: Rather than crawling an entire site at once, the crawler processes URLs in small batches (typically 5 at a time) to stay within the 10-second execution limit of Vercel's free tier.

2. **State Persistence**: Each job's state is stored in a JSON file, allowing the crawl to resume where it left off when a new request is made.

3. **Asynchronous Processing**: The crawler uses `aiohttp` and `asyncio` for efficient parallel requests to maximize throughput within time constraints.

4. **Resource Classification**: Downloaded resources are categorized into HTML, CSS, JavaScript, images, and fonts for organized storage and viewing.

## Important Notes for Vercel

- **10-second Execution Limit**: Vercel's free tier serverless functions have a 10-second execution limit. The crawler is designed to work within this constraint, but larger sites will require multiple "Continue Crawl" requests.

- **Temporary Storage**: Vercel's serverless functions use ephemeral storage. Files stored within the function's environment will persist only for a limited time (typically up to a day) before being cleaned up.

- **Output Directory**: The application uses `/tmp/crawler_output` on Vercel to store crawled content, as specified in the `vercel.json` configuration.

## License

This project is open source and available under the MIT License.

## Responsible Use

Please use Crawlr responsibly:
- Only crawl websites where you have permission
- Respect site owners' rights and robots.txt directives
- Don't overload websites with excessive requests
- Give proper attribution when using archived content

## Running the Application

### Preferred Method (New Interface)
To start the application with the new interface design, use the provided startup script:

```bash
# On Linux/Mac
./start_app.py

# On Windows
python start_app.py
```

This script will:
1. Stop any running instances of the application
2. Clear the cache
3. Start the server with the new interface design

After starting the server, open http://127.0.0.1:5050 in your web browser.

**Important**: If you still see the old interface, perform a hard refresh in your browser:
- Windows/Linux: Ctrl+F5
- Mac: Cmd+Shift+R

### Alternative Method
You can also start the application directly:

```bash
python serverless_api.py
```

**Do not use** `web_interface.py` or `web_interface_retro.py` as these contain the old interface design.
