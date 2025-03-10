#!/usr/bin/env python3
"""
Teller Website Crawler Results Viewer

A simple Flask app to view the crawled content from the Teller website.
"""

import os
import json
from flask import Flask, render_template_string, send_from_directory, redirect

app = Flask(__name__)

# Directory where the crawler saved its output
OUTPUT_DIR = "./teller_output"

@app.route('/')
def index():
    """Display the main index page with links to pages and images."""
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Teller Website Crawler Results</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
            .header {
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }
            .stats {
                margin-bottom: 30px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 8px;
            }
            .nav-buttons {
                display: flex;
                gap: 15px;
                margin-top: 20px;
            }
            .btn {
                display: inline-block;
                padding: 12px 20px;
                background-color: #4a6cf7;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                transition: background-color 0.3s;
                font-weight: bold;
            }
            .btn:hover {
                background-color: #3a56d8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Teller Website Crawler Results</h1>
                <p>This viewer displays content crawled from <a href="https://weareteller.webflow.io/" target="_blank">https://weareteller.webflow.io/</a></p>
            </div>
            
            <div class="stats">
                <h2>Crawl Statistics</h2>
                {% if stats %}
                <p><strong>Pages Crawled:</strong> {{ stats.pages_crawled }}</p>
                <p><strong>Links Found:</strong> {{ stats.links_found }}</p>
                <p><strong>Images Found:</strong> {{ stats.images_found }}</p>
                <p><strong>Start Time:</strong> {{ stats.start_time }}</p>
                <p><strong>End Time:</strong> {{ stats.end_time or 'In Progress...' }}</p>
                {% else %}
                <p>No statistics available. Have you run the crawler yet?</p>
                {% endif %}
            </div>
            
            <div class="nav-buttons">
                <a href="/pages" class="btn">Browse Pages</a>
                <a href="/images" class="btn">View Images</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Get stats if available
    stats = None
    stats_file = os.path.join(OUTPUT_DIR, 'stats', 'crawler_stats.json')
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    
    return render_template_string(template, stats=stats)

@app.route('/pages')
def pages():
    """Display a list of all crawled pages with links."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    if not os.path.exists(html_dir):
        return "No crawled content found. Please run the crawler first."
    
    html_files = os.listdir(html_dir)
    html_files = [f for f in html_files if f.endswith('.html')]
    html_files.sort()
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Teller Website - Crawled Pages</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
            .header {
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }
            .page-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .page-item {
                background-color: #f9f9f9;
                border-radius: 6px;
                padding: 15px;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .page-item:hover {
                transform: translateY(-3px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .page-item a {
                color: #4a6cf7;
                text-decoration: none;
                font-weight: bold;
                display: block;
                word-break: break-word;
            }
            .page-item a:hover {
                text-decoration: underline;
            }
            .nav-buttons {
                margin-top: 30px;
            }
            .btn {
                display: inline-block;
                padding: 12px 20px;
                background-color: #4a6cf7;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                transition: background-color 0.3s;
                font-weight: bold;
            }
            .btn:hover {
                background-color: #3a56d8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Teller Website - Crawled Pages</h1>
                <p>Showing {{ html_files|length }} crawled pages</p>
            </div>
            
            <div class="page-list">
                {% for file in html_files %}
                <div class="page-item">
                    <a href="/view/{{ file }}">{{ file }}</a>
                </div>
                {% endfor %}
            </div>
            
            <div class="nav-buttons">
                <a href="/" class="btn">Back to Home</a>
                <a href="/images" class="btn">View Images</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template, html_files=html_files)

@app.route('/images')
def images():
    """Display an image gallery of all downloaded images."""
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    if not os.path.exists(images_dir):
        return "No images found. Please run the crawler with image downloading."
    
    image_files = []
    for file in os.listdir(images_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            image_files.append(file)
    
    image_files.sort()
    
    # Get image stats if available
    stats = None
    stats_file = os.path.join(OUTPUT_DIR, 'stats', 'image_stats.json')
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Teller Website - Images</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
            .header {
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }
            .stats {
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 8px;
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .gallery-item {
                border: 1px solid #ddd;
                border-radius: 6px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
                background-color: #fff;
            }
            .gallery-item:hover {
                transform: scale(1.03);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .gallery-item img {
                width: 100%;
                height: 200px;
                object-fit: contain;
                background-color: #f9f9f9;
                border-bottom: 1px solid #eee;
                padding: 10px;
                box-sizing: border-box;
                cursor: pointer;
            }
            .gallery-item.svg-item img {
                padding: 20px;
            }
            .image-info {
                padding: 10px 15px;
            }
            .image-info h3 {
                margin: 0 0 5px 0;
                font-size: 14px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .image-info p {
                margin: 5px 0 0;
                font-size: 12px;
                color: #777;
            }
            .nav-buttons {
                margin-top: 30px;
            }
            .btn {
                display: inline-block;
                padding: 12px 20px;
                background-color: #4a6cf7;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                transition: background-color 0.3s;
                font-weight: bold;
            }
            .btn:hover {
                background-color: #3a56d8;
            }
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.8);
            }
            .modal-content {
                display: block;
                margin: auto;
                max-width: 90%;
                max-height: 90%;
                padding: 20px 0;
                position: relative;
                top: 50%;
                transform: translateY(-50%);
            }
            .modal-content img {
                display: block;
                margin: auto;
                max-width: 100%;
                max-height: 80vh;
                border: 2px solid white;
            }
            .modal-caption {
                text-align: center;
                color: white;
                padding: 10px;
                font-size: 16px;
            }
            .close {
                position: absolute;
                top: 15px;
                right: 20px;
                color: white;
                font-size: 40px;
                font-weight: bold;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Teller Website - Images</h1>
                <p>Showing {{ image_files|length }} downloaded images</p>
            </div>
            
            {% if stats %}
            <div class="stats">
                <h2>Image Statistics</h2>
                <p><strong>Images Found:</strong> {{ stats.images_found }}</p>
                <p><strong>Images Downloaded:</strong> {{ stats.images_downloaded }}</p>
                <p><strong>Total Download Size:</strong> {{ stats.bytes_downloaded }} bytes ({{ stats.bytes_downloaded / 1024 | int }} KB)</p>
            </div>
            {% endif %}
            
            {% if image_files %}
            <div class="gallery">
                {% for image in image_files %}
                <div class="gallery-item {% if image.endswith('.svg') %}svg-item{% endif %}" onclick="openModal('{{ image }}')">
                    <img src="/image-file/{{ image }}" alt="{{ image }}">
                    <div class="image-info">
                        <h3>{{ image }}</h3>
                        <p>Click to view larger</p>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No images found. Make sure you've run the crawler with image downloading enabled.</p>
            {% endif %}
            
            <div class="nav-buttons">
                <a href="/" class="btn">Back to Home</a>
                <a href="/pages" class="btn">Browse Pages</a>
            </div>
        </div>
        
        <!-- Modal for larger image view -->
        <div id="imageModal" class="modal">
            <span class="close" onclick="closeModal()">&times;</span>
            <div class="modal-content">
                <img id="modalImage" src="">
                <div id="modalCaption" class="modal-caption"></div>
            </div>
        </div>
        
        <script>
            function openModal(imageName) {
                document.getElementById('imageModal').style.display = 'block';
                document.getElementById('modalImage').src = '/image-file/' + imageName;
                document.getElementById('modalCaption').innerHTML = imageName;
            }
            
            function closeModal() {
                document.getElementById('imageModal').style.display = 'none';
            }
            
            // Close modal when clicking outside the image
            window.onclick = function(event) {
                const modal = document.getElementById('imageModal');
                if (event.target == modal) {
                    closeModal();
                }
            }
            
            // Close modal with Escape key
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    closeModal();
                }
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(template, image_files=image_files, stats=stats)

@app.route('/view/<filename>')
def view_page(filename):
    """View a specific crawled page."""
    html_dir = os.path.join(OUTPUT_DIR, 'html')
    # Ensure the requested file exists
    if not os.path.exists(os.path.join(html_dir, filename)):
        return redirect('/pages')
    
    # Serve the file
    return send_from_directory(html_dir, filename)

@app.route('/image-file/<filename>')
def image_file(filename):
    """Serve an image file."""
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    return send_from_directory(images_dir, filename)

if __name__ == '__main__':
    print("Teller Website Results Viewer starting at http://127.0.0.1:5003")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, port=5003) 