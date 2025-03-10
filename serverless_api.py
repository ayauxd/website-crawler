import os
import json
import uuid
import time
import asyncio
import logging
import datetime
from pathlib import Path
from glob import glob

from flask import Flask, request, jsonify, render_template, send_from_directory
from serverless_crawler import ServerlessCrawler, run_crawler

# Debug message at startup
print("DEBUG: Starting server using serverless_api.py")
print("DEBUG: Template folder path: templates")
print("DEBUG: Static folder path: " + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

# Verify environment and setup proper paths for Vercel
IS_VERCEL = os.environ.get('VERCEL', '0') == '1'
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/tmp/crawler_output' if IS_VERCEL else './output')
MAX_PAGES = int(os.environ.get('MAX_PAGES', 50))
MAX_DEPTH = int(os.environ.get('MAX_DEPTH', 3))

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dictionary to track active jobs
active_jobs = {}
completed_jobs = {}

# Add disclaimer message
DISCLAIMER = """
Crawlr is a web archiving tool for educational and personal use.

Please use responsibly and respect website owners' rights, robots.txt directives, and rate limits.
"""

# Load existing job data
def load_jobs():
    """Load existing jobs from the output directory"""
    global active_jobs, completed_jobs
    
    # Reset dictionaries
    active_jobs = {}
    completed_jobs = {}
    
    # Check for job directories
    try:
        job_dirs = [d for d in glob(f"{OUTPUT_DIR}/*") if os.path.isdir(d)]
        
        for job_dir in job_dirs:
            job_id = os.path.basename(job_dir)
            state_file = os.path.join(job_dir, "state.json")
            stats_file = os.path.join(job_dir, "stats.json")
            
            if os.path.exists(state_file) and os.path.exists(stats_file):
                try:
                    # Load job state
                    with open(state_file, 'r') as f:
                        state = json.load(f)
                    
                    # Load job stats
                    with open(stats_file, 'r') as f:
                        stats = json.load(f)
                    
                    # Determine if job is active or completed
                    if state.get("status") == "completed":
                        completed_jobs[job_id] = {
                            "id": job_id,
                            "url": state.get("url"),
                            "date": datetime.datetime.fromisoformat(state.get("start_time")).strftime("%Y-%m-%d %H:%M"),
                            "pages": stats.get("pages_crawled", 0),
                            "resources": stats.get("resources", {}),
                            "links_found": stats.get("links_found", 0)
                        }
                    else:
                        # Calculate progress
                        queue_size = len(state.get("queue", []))
                        in_progress_size = len(state.get("in_progress", []))
                        visited_size = len(state.get("visited", []))
                        total_urls = queue_size + in_progress_size + visited_size
                        
                        progress = 0
                        if total_urls > 0:
                            progress = int((visited_size / total_urls) * 100)
                        
                        active_jobs[job_id] = {
                            "id": job_id,
                            "url": state.get("url"),
                            "status": state.get("status", "paused"),
                            "pages_completed": visited_size,
                            "max_pages": MAX_PAGES,
                            "progress": progress,
                            "last_run": state.get("last_run")
                        }
                except Exception as e:
                    logger.error(f"Error loading job {job_id}: {e}")
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        # In Vercel, this might fail on cold starts, which is fine
    
    # Return both dictionaries
    return active_jobs, completed_jobs

# Call load_jobs on startup (but not on Vercel cold start which might cause issues)
if not IS_VERCEL:
    load_jobs()

@app.route('/')
def index():
    """Render the main page with crawler interface and archives."""
    print("DEBUG: serverless_api.py index route accessed")
    logger.info("DEBUG: serverless_api.py index route accessed")
    
    # Load completed archives
    completed_jobs_data = {}
    active_jobs_data = {}
    
    # Get data for completed jobs
    for job_id, job_data in completed_jobs.items():
        completed_jobs_data[job_id] = job_data
    
    # Get data for active jobs
    for job_id, job_data in active_jobs.items():
        active_jobs_data[job_id] = job_data
    
    # Calculate progress and other stats
    progress = 0
    pages_completed = 0
    
    print(f"DEBUG: Rendering template 'index.html' with progress={progress}, pages_completed={pages_completed}")
    print(f"DEBUG: Active jobs: {len(active_jobs)}, Completed jobs: {len(completed_jobs)}")
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'index.html')
    print(f"DEBUG: Template path being checked: {template_path}")
    print(f"DEBUG: Template exists: {os.path.exists(template_path)}")
    
    # Add current time for cache busting
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    return render_template(
        'index.html',
        active_jobs=active_jobs_data,
        completed_jobs=completed_jobs_data,
        progress=progress,
        pages_completed=pages_completed,
        now=now,
        disclaimer=DISCLAIMER
    )

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    """Start a new crawl job"""
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Create a new job ID
        job_id = str(uuid.uuid4())
        output_dir = os.path.join(OUTPUT_DIR, job_id)
        
        # Initialize crawler
        crawler = ServerlessCrawler(
            base_url=url,
            job_id=job_id,
            output_dir=output_dir,
            max_pages=MAX_PAGES,
            max_depth=MAX_DEPTH
        )
        
        # Run the first batch asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(crawler.process_batch())
        loop.close()
        
        # Add to active jobs
        active_jobs[job_id] = {
            "id": job_id,
            "url": url,
            "status": "started",
            "pages_completed": crawler.state["pages_crawled"],
            "max_pages": MAX_PAGES,
            "progress": int((crawler.state["pages_crawled"] / MAX_PAGES) * 100) if MAX_PAGES > 0 else 0,
            "last_run": datetime.datetime.now().isoformat()
        }
        
        # Return job information
        return jsonify({
            "job_id": job_id,
            "url": url,
            "status": "started",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error starting crawl: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/continue_crawl/<job_id>', methods=['POST'])
def continue_crawl(job_id):
    """Continue a previously started crawl job"""
    if job_id not in active_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    try:
        # Get job output directory
        output_dir = os.path.join(OUTPUT_DIR, job_id)
        state_file = os.path.join(output_dir, "state.json")
        
        if not os.path.exists(state_file):
            return jsonify({"error": "Job state not found"}), 404
        
        # Load state to get the original URL
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        url = state.get("url")
        if not url:
            return jsonify({"error": "URL not found in job state"}), 400
        
        # Continue crawling
        crawler = ServerlessCrawler(
            base_url=url,
            job_id=job_id,
            output_dir=output_dir,
            max_pages=MAX_PAGES,
            max_depth=MAX_DEPTH
        )
        
        # Run the next batch asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(crawler.process_batch())
        loop.close()
        
        # Update job status
        job_status = "running"
        if result.get("status") == "completed":
            job_status = "completed"
            
            # Move from active to completed
            if job_id in active_jobs:
                job_data = active_jobs[job_id]
                completed_jobs[job_id] = {
                    "id": job_id,
                    "url": url,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "crawled_count": crawler.state["pages_crawled"],
                    "resources": crawler.state["resources_downloaded"],
                    "links_found": len(crawler.state["links_found"])
                }
                del active_jobs[job_id]
        else:
            # Update active job info
            active_jobs[job_id] = {
                "id": job_id,
                "url": url,
                "status": job_status,
                "pages_completed": crawler.state["pages_crawled"],
                "max_pages": MAX_PAGES,
                "progress": int((crawler.state["pages_crawled"] / MAX_PAGES) * 100) if MAX_PAGES > 0 else 0,
                "last_run": datetime.datetime.now().isoformat()
            }
        
        return jsonify({
            "job_id": job_id,
            "status": job_status,
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error continuing crawl for job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/job_status/<job_id>')
def job_status(job_id):
    """Get the status of a job"""
    # Check active jobs first
    if job_id in active_jobs:
        return jsonify(active_jobs[job_id])
    
    # Then check completed jobs
    if job_id in completed_jobs:
        return jsonify(completed_jobs[job_id])
    
    # Try to load from disk if not in memory
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    state_file = os.path.join(output_dir, "state.json")
    stats_file = os.path.join(output_dir, "stats.json")
    
    if os.path.exists(state_file) and os.path.exists(stats_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            return jsonify({
                "id": job_id,
                "url": state.get("url"),
                "status": state.get("status"),
                "pages_completed": stats.get("pages_crawled", 0),
                "max_pages": MAX_PAGES,
                "progress": int((stats.get("pages_crawled", 0) / MAX_PAGES) * 100) if MAX_PAGES > 0 else 0,
                "last_run": state.get("last_run")
            })
        except Exception as e:
            logger.error(f"Error loading job status for {job_id}: {e}")
    
    return jsonify({"error": "Job not found"}), 404

@app.route('/view/<job_id>')
def view_archive(job_id):
    """View the results of a crawl"""
    # Check if job exists
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    html_dir = os.path.join(output_dir, "html")
    state_file = os.path.join(output_dir, "state.json")
    stats_file = os.path.join(output_dir, "stats.json")
    
    if not os.path.exists(output_dir) or not os.path.exists(state_file):
        return render_template('error.html', message=f"Archive with ID {job_id} not found")
    
    try:
        # Load state and stats
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        # Get list of HTML files
        html_files = []
        if os.path.exists(html_dir):
            html_files = [os.path.basename(f) for f in glob(f"{html_dir}/*.html")]
        
        # Count resources
        resource_counts = {
            "css": len(glob(f"{output_dir}/css/*")),
            "js": len(glob(f"{output_dir}/js/*")),
            "images": len(glob(f"{output_dir}/images/*")),
            "fonts": len(glob(f"{output_dir}/fonts/*"))
        }
        
        return render_template('archive.html', 
                              job_id=job_id,
                              url=state.get("url", "Unknown URL"),
                              date=datetime.datetime.fromisoformat(state.get("start_time")).strftime("%Y-%m-%d %H:%M"),
                              pages_crawled=stats.get("pages_crawled", 0),
                              links_found=stats.get("links_found", 0),
                              resource_counts=resource_counts,
                              html_files=html_files,
                              disclaimer=DISCLAIMER)
    
    except Exception as e:
        logger.error(f"Error viewing archive {job_id}: {e}")
        return render_template('error.html', message=f"Error loading archive: {str(e)}")

@app.route('/api/clean_job/<job_id>', methods=['POST'])
def clean_job(job_id):
    """Remove a job and its files"""
    # Check if job exists
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    
    if not os.path.exists(output_dir):
        return jsonify({"error": "Job not found"}), 404
    
    try:
        # Remove from tracking dictionaries
        if job_id in active_jobs:
            del active_jobs[job_id]
        
        if job_id in completed_jobs:
            del completed_jobs[job_id]
        
        # Remove directory and all contents
        import shutil
        shutil.rmtree(output_dir)
        
        return jsonify({"success": True, "message": f"Job {job_id} removed"})
    
    except Exception as e:
        logger.error(f"Error cleaning job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/job/<job_id>/<path:resource_path>')
def serve_job_file(job_id, resource_path):
    """Serve a file from the job directory"""
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    return send_from_directory(job_dir, resource_path)

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    print(f"DEBUG: Serving static file: {path}")
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    print(f"DEBUG: Static directory: {static_dir}")
    return send_from_directory(static_dir, path)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon directly"""
    print("DEBUG: Serving favicon.ico")
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

@app.route('/api/resources/<resource_type>/<job_id>')
def list_resources(resource_type, job_id):
    """List resources of a specific type for a job"""
    # Validate resource type
    if resource_type not in ['css', 'js', 'images', 'fonts']:
        return jsonify({"error": "Invalid resource type"}), 400
    
    # Check if job exists
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    if not os.path.exists(output_dir):
        return jsonify({"error": "Job not found"}), 404
    
    # Get resource directory path
    resource_dir = os.path.join(output_dir, resource_type)
    
    # Check if resource directory exists
    if not os.path.exists(resource_dir):
        return jsonify({"files": []}), 200
    
    # List files in the directory
    try:
        files = [os.path.basename(f) for f in glob(f"{resource_dir}/*")]
        return jsonify({"files": files})
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/about')
def about():
    """About page with information and instructions"""
    about_content = {
        "title": "About Crawlr",
        "description": "Crawlr is a serverless web archiving tool designed to capture websites for educational and personal use.",
        "features": [
            "Captures entire websites including HTML, CSS, JavaScript, images and fonts",
            "Works within serverless constraints by processing sites in small batches",
            "Archives content in a browsable, organized structure",
            "Allows you to view and download resources for further use"
        ],
        "usage": [
            "Enter a URL to begin crawling a website",
            "The crawler will process pages in batches (due to serverless constraints)",
            "Use 'Continue Crawl' buttons to process larger sites in multiple steps",
            "View completed archives to browse the captured content",
            "Download or copy files for use in your development environment"
        ],
        "ide_instructions": [
            "All archived files maintain their relative paths and relationships",
            "HTML files are stored in the 'html' directory",
            "CSS files are stored in the 'css' directory",
            "JavaScript files are stored in the 'js' directory",
            "Images and fonts are stored in their respective directories",
            "Copy these files to your IDE or development environment maintaining the same structure",
            "Open the HTML files in your browser to view the archived content"
        ]
    }
    return render_template('about.html', 
                          content=about_content,
                          disclaimer=DISCLAIMER)

@app.route('/ide-usage')
def ide_usage():
    """Page explaining how to use Crawlr output in different IDEs"""
    ide_content = {
        "title": "Using Crawlr Output in Your IDE",
        "description": "Crawlr organizes archived websites in a way that makes them easy to import and use in any IDE or code editor.",
        "general_instructions": [
            "After crawling a website, click on 'View Details' to browse the archived content",
            "Navigate through the HTML, CSS, JS, and other resources",
            "Click on any file to view its contents in your browser",
            "Copy the code or download the files to use in your IDE"
        ],
        "ides": [
            {
                "name": "VS Code",
                "steps": [
                    "Create a new folder for your project",
                    "Inside this folder, create subfolders: html, css, js, images, fonts",
                    "Copy the HTML files from Crawlr to your html folder",
                    "Copy CSS, JS, and other resources to their respective folders",
                    "Open the folder in VS Code using File > Open Folder",
                    "Start editing the files to customize the site to your needs"
                ]
            },
            {
                "name": "Sublime Text",
                "steps": [
                    "Create a project folder with the same structure as the Crawlr output",
                    "Copy files from Crawlr to their respective folders",
                    "Use Project > Add Folder to Project to include the entire folder",
                    "Edit the files while maintaining the same relative paths"
                ]
            },
            {
                "name": "JetBrains IDEs (PyCharm, WebStorm, etc.)",
                "steps": [
                    "Create a new project and select an empty template",
                    "Create the same folder structure as Crawlr output",
                    "Copy the files from Crawlr to your project",
                    "JetBrains IDEs will automatically recognize HTML, CSS, and JS files",
                    "Use the built-in preview features to test your changes"
                ]
            }
        ],
        "tips": [
            "Always maintain the same folder structure to preserve file references",
            "Use relative paths (e.g., '../css/style.css') rather than absolute paths",
            "If you encounter missing resources, check if they were properly copied",
            "Use your IDE's search feature to find and modify specific elements or styles",
            "Most IDEs have live preview features to see your changes in real-time"
        ]
    }
    return render_template('ide_usage.html', content=ide_content)

# Add debug information to the main function
if __name__ == "__main__":
    print(f"DEBUG: Starting server using serverless_api.py")
    print(f"DEBUG: Template folder path: {app.template_folder}")
    print(f"DEBUG: Static folder path: {app.static_folder}")
    print("Starting VibeCrawlr - Web Inspiration Tool at http://127.0.0.1:5050")
    app.run(debug=True, host='0.0.0.0', port=5050) 