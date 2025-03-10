#!/usr/bin/env python3
"""
Teller Website Crawler Results Viewer

A simple Flask app to view the crawled content from the Teller website.
"""

import os
import json
from flask import Flask, render_template, abort, send_from_directory, redirect, url_for

app = Flask(__name__)

# Directory where the crawler saved its output
OUTPUT_DIR = "./teller_output"

@app.route('/')
def index():
    """Display the list of crawled pages."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    
    if not os.path.exists(html_dir):
        return "No crawled pages found. Run teller_crawler.py first."
    
    pages = []
    for filename in os.listdir(html_dir):
        if filename.endswith('.html'):
            file_path = os.path.join(html_dir, filename)
            url_path = '/' + filename
            
            # Get file size
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB"
            
            pages.append({
                'filename': filename,
                'url': url_path,
                'size': size_str
            })
    
    # Sort pages by filename
    pages.sort(key=lambda x: x['filename'])
    
    return render_template('teller_pages_list.html', pages=pages, title="Teller Website Results")

@app.route('/<path:filename>')
def serve_html(filename):
    """Serve an HTML file."""
    if not filename.endswith('.html'):
        filename += '.html'
        
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    return send_from_directory(html_dir, filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve a CSS file."""
    css_dir = os.path.join(OUTPUT_DIR, 'css')
    return send_from_directory(css_dir, filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve a JavaScript file."""
    js_dir = os.path.join(OUTPUT_DIR, 'js')
    return send_from_directory(js_dir, filename)

@app.route('/fonts/<path:filename>')
def serve_font(filename):
    """Serve a font file."""
    fonts_dir = os.path.join(OUTPUT_DIR, 'fonts')
    return send_from_directory(fonts_dir, filename)

@app.route('/images')
def image_list():
    """Display a list of all downloaded images."""
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    
    if not os.path.exists(images_dir):
        return "No images found. Run teller_crawler.py first."
    
    images = []
    for filename in os.listdir(images_dir):
        file_path = os.path.join(images_dir, filename)
        url_path = '/image-file/' + filename
        
        # Get file size
        size = os.path.getsize(file_path)
        size_str = f"{size / 1024:.1f} KB"
        
        images.append({
            'filename': filename,
            'url': url_path,
            'size': size_str
        })
    
    # Sort images by filename
    images.sort(key=lambda x: x['filename'])
    
    return render_template('teller_images_list.html', images=images, title="Teller Website Images")

@app.route('/image-file/<path:filename>')
def serve_image(filename):
    """Serve an image file."""
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/stats')
def show_stats():
    """Display crawling statistics."""
    stats_file = os.path.join(OUTPUT_DIR, 'stats', 'crawler_stats.json')
    
    if not os.path.exists(stats_file):
        return "No stats found. Run teller_crawler.py first."
    
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    return render_template('teller_stats.html', stats=stats, title="Teller Crawler Statistics")

@app.route('/resources')
def show_resources():
    """Display a list of downloaded CSS, JS, and font resources."""
    css_dir = os.path.join(OUTPUT_DIR, 'css')
    js_dir = os.path.join(OUTPUT_DIR, 'js')
    fonts_dir = os.path.join(OUTPUT_DIR, 'fonts')
    
    resources = {
        'css': [],
        'js': [],
        'fonts': []
    }
    
    # Get CSS files
    if os.path.exists(css_dir):
        for filename in os.listdir(css_dir):
            file_path = os.path.join(css_dir, filename)
            url_path = '/css/' + filename
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB"
            resources['css'].append({
                'filename': filename,
                'url': url_path,
                'size': size_str
            })
    
    # Get JS files
    if os.path.exists(js_dir):
        for filename in os.listdir(js_dir):
            file_path = os.path.join(js_dir, filename)
            url_path = '/js/' + filename
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB"
            resources['js'].append({
                'filename': filename,
                'url': url_path,
                'size': size_str
            })
    
    # Get font files
    if os.path.exists(fonts_dir):
        for filename in os.listdir(fonts_dir):
            file_path = os.path.join(fonts_dir, filename)
            url_path = '/fonts/' + filename
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB"
            resources['fonts'].append({
                'filename': filename,
                'url': url_path,
                'size': size_str
            })
    
    # Sort all resource lists by filename
    resources['css'].sort(key=lambda x: x['filename'])
    resources['js'].sort(key=lambda x: x['filename'])
    resources['fonts'].sort(key=lambda x: x['filename'])
    
    return render_template('teller_resources.html', resources=resources, title="Teller Website Resources")

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create template files if they don't exist
    with open('templates/teller_pages_list.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .page-list { list-style: none; padding: 0; }
                .page-item { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                .page-link { color: #0066cc; text-decoration: none; font-weight: bold; }
                .page-info { color: #666; font-size: 0.9em; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            
            <div class="nav">
                <a href="/">Pages</a>
                <a href="/stats">Statistics</a>
                <a href="/images">Images</a>
                <a href="/resources">Resources</a>
            </div>
            
            <h2>Crawled Pages</h2>
            <p>Click on a page to view it:</p>
            
            <ul class="page-list">
                {% for page in pages %}
                <li class="page-item">
                    <a class="page-link" href="{{ page.url }}">{{ page.filename }}</a>
                    <div class="page-info">Size: {{ page.size }}</div>
                </li>
                {% endfor %}
            </ul>
        </body>
        </html>
        ''')
    
    with open('templates/teller_stats.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .stats-container { border: 1px solid #ddd; padding: 20px; border-radius: 4px; }
                .stat-item { display: flex; margin: 10px 0; }
                .stat-label { font-weight: bold; width: 200px; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            
            <div class="nav">
                <a href="/">Pages</a>
                <a href="/stats">Statistics</a>
                <a href="/images">Images</a>
                <a href="/resources">Resources</a>
            </div>
            
            <div class="stats-container">
                <div class="stat-item">
                    <div class="stat-label">Pages Crawled:</div>
                    <div class="stat-value">{{ stats.pages_crawled }}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Links Found:</div>
                    <div class="stat-value">{{ stats.links_found }}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Images Found:</div>
                    <div class="stat-value">{{ stats.images_found }}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Resources Downloaded:</div>
                    <div class="stat-value">{{ stats.resources_downloaded }}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Bytes Downloaded:</div>
                    <div class="stat-value">{{ stats.bytes_downloaded }} bytes ({{ stats.bytes_downloaded // 1024 }} KB)</div>
                </div>
            </div>
        </body>
        </html>
        ''')
    
    with open('templates/teller_images_list.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
                .image-item { border: 1px solid #ddd; border-radius: 4px; padding: 10px; text-align: center; }
                .image-preview { width: 100%; height: 150px; object-fit: contain; margin-bottom: 10px; }
                .image-name { font-size: 0.8em; word-break: break-all; }
                .image-info { font-size: 0.7em; color: #666; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            
            <div class="nav">
                <a href="/">Pages</a>
                <a href="/stats">Statistics</a>
                <a href="/images">Images</a>
                <a href="/resources">Resources</a>
            </div>
            
            <h2>Downloaded Images ({{ images|length }})</h2>
            
            <div class="image-grid">
                {% for image in images %}
                <div class="image-item">
                    <img class="image-preview" src="{{ image.url }}" alt="{{ image.filename }}">
                    <div class="image-name">{{ image.filename }}</div>
                    <div class="image-info">Size: {{ image.size }}</div>
                </div>
                {% endfor %}
            </div>
        </body>
        </html>
        ''')
    
    with open('templates/teller_resources.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                h1, h2 { color: #333; }
                .resource-section { margin-bottom: 30px; }
                .resource-list { list-style: none; padding: 0; }
                .resource-item { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                .resource-link { color: #0066cc; text-decoration: none; font-weight: bold; }
                .resource-info { color: #666; font-size: 0.9em; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            
            <div class="nav">
                <a href="/">Pages</a>
                <a href="/stats">Statistics</a>
                <a href="/images">Images</a>
                <a href="/resources">Resources</a>
            </div>
            
            <div class="resource-section">
                <h2>CSS Files ({{ resources.css|length }})</h2>
                <ul class="resource-list">
                    {% for resource in resources.css %}
                    <li class="resource-item">
                        <a class="resource-link" href="{{ resource.url }}">{{ resource.filename }}</a>
                        <div class="resource-info">Size: {{ resource.size }}</div>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="resource-section">
                <h2>JavaScript Files ({{ resources.js|length }})</h2>
                <ul class="resource-list">
                    {% for resource in resources.js %}
                    <li class="resource-item">
                        <a class="resource-link" href="{{ resource.url }}">{{ resource.filename }}</a>
                        <div class="resource-info">Size: {{ resource.size }}</div>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="resource-section">
                <h2>Font Files ({{ resources.fonts|length }})</h2>
                <ul class="resource-list">
                    {% for resource in resources.fonts %}
                    <li class="resource-item">
                        <a class="resource-link" href="{{ resource.url }}">{{ resource.filename }}</a>
                        <div class="resource-info">Size: {{ resource.size }}</div>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </body>
        </html>
        ''')
    
    print(f"Teller Website Results Viewer starting at http://127.0.0.1:5003")
    print(f"Press Ctrl+C to stop the server")
    app.run(debug=True, port=5003) 