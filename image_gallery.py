#!/usr/bin/env python3
"""
Image Gallery for Mac Template Website

This script provides a simple web interface to view the images downloaded from
the Mac template website.
"""

import os
import json
from flask import Flask, render_template_string, send_from_directory, redirect

app = Flask(__name__)

# Directory where images are stored
IMAGE_DIR = "./mac_template_output/images"
STATS_DIR = "./mac_template_output/stats"

@app.route('/')
def index():
    """Display an image gallery."""
    if not os.path.exists(IMAGE_DIR):
        return "No images found. Please run the image downloader first."
    
    # Get all image files
    image_files = []
    for file in os.listdir(IMAGE_DIR):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            image_files.append(file)
    
    # Sort by filename
    image_files.sort()
    
    # Get stats if available
    stats = None
    stats_file = os.path.join(STATS_DIR, 'image_stats.json')
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mac Template Image Gallery</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
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
            .stats {
                margin-top: 20px;
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 4px;
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .gallery-item {
                border: 1px solid #ddd;
                border-radius: 4px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .gallery-item:hover {
                transform: scale(1.02);
            }
            .gallery-item img {
                width: 100%;
                height: auto;
                display: block;
            }
            .gallery-item.svg-item {
                padding: 10px;
                background-color: #f9f9f9;
            }
            .gallery-item.svg-item img {
                width: 100%;
                height: 150px;
                object-fit: contain;
            }
            .image-info {
                padding: 10px;
                background-color: #f9f9f9;
            }
            .image-info h3 {
                margin: 0;
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
            .back-button {
                margin-top: 20px;
            }
            .back-button a {
                display: inline-block;
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .back-button a:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mac Template Image Gallery</h1>
            
            {% if stats %}
            <div class="stats">
                <h2>Image Statistics</h2>
                <p><strong>Images Found:</strong> {{ stats.images_found }}</p>
                <p><strong>Images Downloaded:</strong> {{ stats.images_downloaded }}</p>
                <p><strong>Total Download Size:</strong> {{ stats.bytes_downloaded }} bytes ({{ stats.bytes_downloaded / 1024 | int }} KB)</p>
            </div>
            {% endif %}
            
            <h2>Downloaded Images ({{ image_files|length }})</h2>
            
            {% if image_files %}
            <div class="gallery">
                {% for image in image_files %}
                <div class="gallery-item {% if image.endswith('.svg') %}svg-item{% endif %}" onclick="openModal('{{ image }}')">
                    <img src="/images/{{ image }}" alt="{{ image }}">
                    <div class="image-info">
                        <h3>{{ image }}</h3>
                        <p>Click to view larger</p>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No images found.</p>
            {% endif %}
            
            <div class="back-button">
                <a href="http://127.0.0.1:5001">Back to Crawler Results</a>
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
                document.getElementById('modalImage').src = '/images/' + imageName;
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

@app.route('/images/<filename>')
def images(filename):
    """Serve images."""
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == '__main__':
    print("Mac Template Image Gallery starting at http://127.0.0.1:5002")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, port=5002) 