"""
DEPRECATED: This file contains the old web interface and should not be used.
Use serverless_api.py instead for the new interface.
"""

import os
import json
import shutil
import time
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import asyncio
import threading
from simple_crawler import WebsiteCrawler
from src.utils import CrawlerStats

app = Flask(__name__, static_folder="static")
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['ARCHIVES_FOLDER'] = os.path.join(os.getcwd(), 'archives')
app.config['MAX_PAGES'] = 100

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ARCHIVES_FOLDER'], exist_ok=True)

# Store active crawls
active_crawls = {}
completed_crawls = {}

@app.route('/')
def index():
    print("DEBUG: web_interface_retro.py index route accessed")
    app.logger.info("DEBUG: web_interface_retro.py index route accessed")
    # Load completed archives from the archives directory
    archives = []
    for archive_id in os.listdir(app.config['ARCHIVES_FOLDER']):
        archive_path = os.path.join(app.config['ARCHIVES_FOLDER'], archive_id)
        if os.path.isdir(archive_path):
            # Try to load metadata
            metadata_path = os.path.join(archive_path, 'metadata.json')
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        archives.append({
                            'id': archive_id,
                            'url': metadata.get('url', 'Unknown URL'),
                            'date': metadata.get('date', 'Unknown date')
                        })
                except:
                    # If metadata can't be loaded, use minimal info
                    archives.append({
                        'id': archive_id,
                        'url': 'Unknown URL',
                        'date': 'Unknown date'
                    })
    
    # Sort archives by date (newest first)
    archives.sort(key=lambda x: x['date'], reverse=True)
    
    # Add status object for template
    status = {
        'running': len(active_crawls) > 0
    }
    
    # Calculate progress if a crawl is running
    progress = 0
    pages_completed = 0
    total_pages = 0
    
    if active_crawls:
        # Get the first active crawl
        crawl_id, crawl_info = next(iter(active_crawls.items()))
        
        # Calculate progress if stats are available
        if 'stats' in crawl_info and crawl_info['stats']:
            pages_completed = crawl_info['stats'].stats['pages']['crawled']
            total_pages = crawl_info.get('max_pages', 10)
            if total_pages > 0:
                progress = min(int((pages_completed / total_pages) * 100), 100)
    
    return render_template('index.html', 
                          archives=archives[:10], 
                          status=status, 
                          progress=progress,
                          pages_completed=pages_completed,
                          total_pages=total_pages)

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    url = request.form.get('url')
    output_dir = request.form.get('output_dir')
    max_pages = int(request.form.get('max_pages', 30))
    max_depth = int(request.form.get('max_depth', 3))
    
    # Validate inputs
    if not url:
        return redirect(url_for('index'))
    
    # Generate a unique ID for this crawl
    crawl_id = str(uuid.uuid4())
    
    # Create a directory for this crawl
    crawl_dir = os.path.join(app.config['UPLOAD_FOLDER'], crawl_id)
    os.makedirs(crawl_dir, exist_ok=True)
    
    # Update the output directory to include our crawl ID
    output_path = os.path.join(crawl_dir, output_dir or 'output')
    
    # Start crawler in a background thread
    thread = threading.Thread(
        target=start_crawler_thread,
        args=(crawl_id, url, output_path, max_pages, max_depth)
    )
    thread.daemon = True
    thread.start()
    
    # Store crawl metadata
    active_crawls[crawl_id] = {
        'url': url,
        'output_dir': output_path,
        'max_pages': max_pages,
        'max_depth': max_depth,
        'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'running',
        'progress': 0,
        'pages_completed': 0,
        'total_pages': max_pages
    }
    
    return redirect(url_for('crawl_status', crawl_id=crawl_id))

def start_crawler_thread(crawl_id, url, output_dir, max_pages, max_depth):
    try:
        # Create and run the crawler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start the crawler asynchronously
        crawler = WebsiteCrawler(url, output_dir=output_dir, max_pages=max_pages, max_depth=max_depth)
        stats = loop.run_until_complete(crawler.crawl())
        
        # Move the crawled content to archives
        archive_dir = os.path.join(app.config['ARCHIVES_FOLDER'], crawl_id)
        os.makedirs(archive_dir, exist_ok=True)
        
        # Copy the crawled files to the archive
        for item in os.listdir(output_dir):
            src = os.path.join(output_dir, item)
            dst = os.path.join(archive_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        # Create a metadata file
        metadata = {
            'url': url,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'max_pages': max_pages,
            'max_depth': max_depth,
            'completed': True
        }
        
        with open(os.path.join(archive_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)
        
        # Update crawl status
        crawl_data = active_crawls.pop(crawl_id, {})
        crawl_data['status'] = 'completed'
        crawl_data['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        completed_crawls[crawl_id] = crawl_data
        
    except Exception as e:
        # Update crawl status with error
        crawl_data = active_crawls.pop(crawl_id, {})
        crawl_data['status'] = 'error'
        crawl_data['error'] = str(e)
        completed_crawls[crawl_id] = crawl_data

@app.route('/crawl/<crawl_id>')
def crawl_status(crawl_id):
    # Check if the crawl is active
    if crawl_id in active_crawls:
        crawl_data = active_crawls[crawl_id]
        return render_template('results.html', 
                              url=crawl_data['url'],
                              crawl_id=crawl_id,
                              status='running',
                              progress=crawl_data['progress'],
                              pages_completed=crawl_data['pages_completed'],
                              total_pages=crawl_data['total_pages'],
                              stats={
                                  'pages_crawled': crawl_data.get('pages_completed', 0),
                                  'html_files': 0,
                                  'css_files': 0,
                                  'js_files': 0,
                                  'images': 0,
                                  'fonts': 0,
                                  'total_size_kb': 0,
                                  'crawl_time': int(time.time() - datetime.strptime(crawl_data['start_time'], '%Y-%m-%d %H:%M:%S').timestamp())
                              })
    
    # Check if the crawl is in completed crawls
    elif crawl_id in completed_crawls:
        return redirect(url_for('view_archive', archive_id=crawl_id))
    
    # Check if the crawl exists in archives
    archive_path = os.path.join(app.config['ARCHIVES_FOLDER'], crawl_id)
    if os.path.exists(archive_path):
        return redirect(url_for('view_archive', archive_id=crawl_id))
    
    # Crawl not found
    return redirect(url_for('index'))

@app.route('/view/<archive_id>')
def view_archive(archive_id):
    archive_path = os.path.join(app.config['ARCHIVES_FOLDER'], archive_id)
    
    if not os.path.exists(archive_path):
        return redirect(url_for('index'))
    
    # Load metadata
    metadata_path = os.path.join(archive_path, 'metadata.json')
    url = "Unknown URL"
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                url = metadata.get('url', url)
        except:
            pass
    
    # Calculate statistics
    stats = {
        'pages_crawled': 0,
        'html_files': 0,
        'css_files': 0,
        'js_files': 0,
        'images': 0,
        'fonts': 0,
        'total_size_kb': 0,
        'crawl_time': 0
    }
    
    # Load stats from stats file if exists
    stats_path = os.path.join(archive_path, 'stats', 'crawler_stats.json')
    if os.path.exists(stats_path):
        try:
            with open(stats_path, 'r') as f:
                stats_data = json.load(f)
                
                # Update stats with actual values
                stats['pages_crawled'] = stats_data.get('pages_crawled', 0)
                stats['crawl_time'] = stats_data.get('crawl_time_seconds', 0)
        except:
            pass
    
    # Count HTML files
    html_dir = os.path.join(archive_path, 'html')
    if os.path.exists(html_dir):
        html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
        stats['html_files'] = len(html_files)
        
        # Generate HTML files list for display
        pages = []
        for html_file in html_files:
            file_path = os.path.join(html_dir, html_file)
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            pages.append({
                'path': f'html/{html_file}',
                'url': html_file,
                'size_kb': size_kb
            })
            stats['total_size_kb'] += size_kb
    else:
        pages = []
    
    # Count CSS files
    css_dir = os.path.join(archive_path, 'css')
    css_files = []
    if os.path.exists(css_dir):
        css_file_list = [f for f in os.listdir(css_dir) if f.endswith('.css')]
        stats['css_files'] = len(css_file_list)
        
        # Generate CSS files list for display
        for css_file in css_file_list:
            file_path = os.path.join(css_dir, css_file)
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            css_files.append({
                'filename': css_file,
                'url': css_file,
                'size_kb': size_kb
            })
            stats['total_size_kb'] += size_kb
    
    # Count JS files
    js_dir = os.path.join(archive_path, 'js')
    js_files = []
    if os.path.exists(js_dir):
        js_file_list = [f for f in os.listdir(js_dir) if f.endswith('.js')]
        stats['js_files'] = len(js_file_list)
        
        # Generate JS files list for display
        for js_file in js_file_list:
            file_path = os.path.join(js_dir, js_file)
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            js_files.append({
                'filename': js_file,
                'url': js_file,
                'size_kb': size_kb
            })
            stats['total_size_kb'] += size_kb
    
    # Count images
    images_dir = os.path.join(archive_path, 'images')
    images = []
    if os.path.exists(images_dir):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
        image_files = []
        for ext in image_extensions:
            image_files.extend([f for f in os.listdir(images_dir) if f.lower().endswith(ext)])
        
        stats['images'] = len(image_files)
        
        # Generate images list for display
        for img_file in image_files:
            file_path = os.path.join(images_dir, img_file)
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            images.append({
                'filename': img_file,
                'size_kb': size_kb
            })
            stats['total_size_kb'] += size_kb
    
    # Count fonts
    fonts_dir = os.path.join(archive_path, 'fonts')
    fonts = []
    if os.path.exists(fonts_dir):
        font_extensions = ['.woff', '.woff2', '.ttf', '.otf', '.eot']
        font_files = []
        for ext in font_extensions:
            font_files.extend([f for f in os.listdir(fonts_dir) if f.lower().endswith(ext)])
        
        stats['fonts'] = len(font_files)
        
        # Generate fonts list for display
        for font_file in font_files:
            file_path = os.path.join(fonts_dir, font_file)
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            fonts.append({
                'filename': font_file,
                'url': font_file,
                'size_kb': size_kb
            })
            stats['total_size_kb'] += size_kb
    
    # Round total size
    stats['total_size_kb'] = round(stats['total_size_kb'], 1)
    
    return render_template('results.html', 
                          url=url,
                          crawl_id=archive_id,
                          status='completed',
                          stats=stats,
                          pages=pages,
                          css_files=css_files,
                          js_files=js_files,
                          images=images,
                          fonts=fonts)

@app.route('/view/<archive_id>/<path:filename>')
def serve_archive_file(archive_id, filename):
    archive_path = os.path.join(app.config['ARCHIVES_FOLDER'], archive_id)
    
    # Determine the type of file to serve
    file_path = os.path.join(archive_path, filename)
    
    # Check if path exists
    if not os.path.exists(file_path):
        return "File not found", 404
    
    # If it's an HTML file, modify links to point to our server
    if filename.endswith('.html'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Return the file
        return content
    
    # For all other files, serve directly
    directory = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    return send_from_directory(directory, file_name)

@app.route('/download/<archive_id>')
def download_archive(archive_id):
    archive_path = os.path.join(app.config['ARCHIVES_FOLDER'], archive_id)
    
    if not os.path.exists(archive_path):
        return redirect(url_for('index'))
    
    # Create a zip file of the archive
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{archive_id}.zip')
    
    if not os.path.exists(zip_path):
        shutil.make_archive(
            os.path.join(app.config['UPLOAD_FOLDER'], archive_id),
            'zip',
            archive_path
        )
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        f'{archive_id}.zip',
        as_attachment=True,
        download_name=f'cut-n-sew-crawl-{archive_id}.zip'
    )

@app.route('/api/crawl-status/<crawl_id>')
def api_crawl_status(crawl_id):
    if crawl_id not in active_crawls:
        return jsonify({'status': 'not_found'})
    
    crawl_data = active_crawls[crawl_id]
    
    # Check the stats directory for updates
    output_dir = crawl_data['output_dir']
    stats_path = os.path.join(output_dir, 'stats', 'crawler_stats.json')
    
    if os.path.exists(stats_path):
        try:
            with open(stats_path, 'r') as f:
                stats_data = json.load(f)
                
                # Update progress information
                crawl_data['pages_completed'] = stats_data.get('pages_crawled', 0)
                crawl_data['progress'] = min(
                    100, 
                    int((crawl_data['pages_completed'] / crawl_data['total_pages']) * 100)
                )
        except:
            pass
    
    return jsonify({
        'status': crawl_data['status'],
        'progress': crawl_data['progress'],
        'pages_completed': crawl_data['pages_completed'],
        'total_pages': crawl_data['total_pages']
    })

if __name__ == '__main__':
    print("Cut n Sew Web Crawler starting at http://127.0.0.1:5050")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, port=5050) 