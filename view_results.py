#!/usr/bin/env python3
"""
Crawler Results Viewer

A simple Flask app to view the crawled content from the Mac template website.
"""

import os
import json
from flask import Flask, render_template, abort, send_from_directory, redirect, url_for

app = Flask(__name__)

# Directory where the crawler saved its output
OUTPUT_DIR = "./mac_template_output"

@app.route('/')
def index():
    """Display the list of crawled pages."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    
    if not os.path.exists(html_dir):
        return "No crawled pages found. Run simple_crawler.py first."
    
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
    
    return render_template('pages_list.html', pages=pages, title="Mac Template Crawler Results")

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

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve an image file."""
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/stats')
def show_stats():
    """Display crawling statistics."""
    stats_file = os.path.join(OUTPUT_DIR, 'stats', 'crawler_stats.json')
    
    if not os.path.exists(stats_file):
        return "No stats found. Run simple_crawler.py first."
    
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    return render_template('stats.html', stats=stats, title="Crawler Statistics")

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create template files if they don't exist
    with open('templates/pages_list.html', 'w') as f:
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
    
    with open('templates/stats.html', 'w') as f:
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
    
    print(f"Mac Template Crawler Results Viewer starting at http://127.0.0.1:5001")
    print(f"Press Ctrl+C to stop the server")
    app.run(debug=True, port=5001) 