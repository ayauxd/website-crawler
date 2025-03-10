#!/usr/bin/env python3
"""
Crawler Results Viewer

A simple Flask app to view the crawled content from the Mac template website.
"""

import os
import json
from flask import Flask, render_template_string, send_from_directory, redirect

app = Flask(__name__)

# Directory where the crawler saved its output
OUTPUT_DIR = "./mac_template_output"

@app.route('/')
def index():
    """Display a list of all crawled pages with links."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    if not os.path.exists(html_dir):
        return "No crawled content found. Please run the crawler first."
    
    html_files = os.listdir(html_dir)
    html_files = [f for f in html_files if f.endswith('.html')]
    
    # Check for stats file
    stats = None
    stats_file = os.path.join(OUTPUT_DIR, 'stats', 'crawler_stats.json')
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mac Template Crawler Results</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1, h2 {
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .page-list {
                margin-top: 20px;
            }
            .page-list a {
                display: block;
                padding: 10px;
                margin-bottom: 5px;
                background-color: #f9f9f9;
                border-radius: 4px;
                color: #0066cc;
                text-decoration: none;
            }
            .page-list a:hover {
                background-color: #e9e9e9;
            }
            .stats {
                margin-top: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 4px;
            }
            .refresh {
                margin-top: 20px;
                text-align: center;
            }
            .refresh a {
                display: inline-block;
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .refresh a:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mac Template Crawler Results</h1>
            
            {% if stats %}
            <div class="stats">
                <h2>Crawler Statistics</h2>
                <p><strong>Pages Crawled:</strong> {{ stats.pages_crawled }}</p>
                <p><strong>Links Found:</strong> {{ stats.links_found }}</p>
                <p><strong>Images Found:</strong> {{ stats.images_found }}</p>
                <p><strong>Start Time:</strong> {{ stats.start_time }}</p>
                <p><strong>End Time:</strong> {{ stats.end_time or 'In Progress...' }}</p>
            </div>
            {% endif %}
            
            <h2>Crawled Pages ({{ html_files|length }})</h2>
            <div class="page-list">
                {% for file in html_files %}
                <a href="/view/{{ file }}">{{ file }}</a>
                {% endfor %}
            </div>
            
            <div class="refresh">
                <a href="/">Refresh</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, html_files=html_files, stats=stats)

@app.route('/view/<filename>')
def view_page(filename):
    """View a specific crawled page."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    # Ensure the requested file exists
    if not os.path.exists(os.path.join(html_dir, filename)):
        return redirect('/')
    
    # Serve the file
    return send_from_directory(html_dir, filename)

if __name__ == '__main__':
    print("Mac Template Crawler Results Viewer starting at http://127.0.0.1:5001")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, port=5001) 