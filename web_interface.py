#!/usr/bin/env python3
"""
Web Interface for the Website Crawler

This script provides a simple web interface for controlling and monitoring the website crawler.
"""
import os
import sys
import json
import time
import datetime
import threading
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__, template_folder='templates')

# Store crawler status
crawler_status = {
    'running': False,
    'url': None,
    'output_dir': None,
    'start_time': None,
    'stats': {},
    'process': None
}

@app.route('/')
def index():
    return render_template('index.html', status=crawler_status)

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    output_dir = request.form.get('output_dir', './output')
    js_rendering = 'js_rendering' in request.form
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Build command
    cmd = [
        'python', 
        'main.py', 
        url, 
        '--output-dir', output_dir
    ]
    
    if js_rendering:
        cmd.append('--js-rendering')
    
    try:
        # Run as background process
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True
        )
        
        # Update status
        crawler_status['running'] = True
        crawler_status['url'] = url
        crawler_status['output_dir'] = output_dir
        crawler_status['start_time'] = datetime.datetime.now().isoformat()
        crawler_status['process'] = process
        
        # Monitor process in background
        thread = threading.Thread(target=monitor_process, args=(process,))
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop_crawl', methods=['POST'])
def stop_crawl():
    if crawler_status['running'] and crawler_status['process']:
        try:
            crawler_status['process'].terminate()
            crawler_status['running'] = False
            return redirect(url_for('index'))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'No crawler running'}), 400

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(crawler_status)

def monitor_process(process):
    """Monitor the crawler process and update status"""
    while process.poll() is None:
        time.sleep(2)
        
        # Try to read any stats file
        if crawler_status['output_dir']:
            stats_path = os.path.join(crawler_status['output_dir'], 'stats', 'crawler_stats.json')
            if os.path.exists(stats_path):
                try:
                    with open(stats_path, 'r') as f:
                        crawler_status['stats'] = json.load(f)
                except:
                    pass
    
    # Process finished
    crawler_status['running'] = False

def create_templates():
    """Create the HTML templates for the web interface"""
    os.makedirs('templates', exist_ok=True)
    
    # Create index.html
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Crawler Interface</title>
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
            h1 {
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            form {
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="text"], input[type="url"] {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .checkbox-group {
                margin-top: 5px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .status-panel {
                margin-top: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 4px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 10px;
                margin-top: 15px;
            }
            .stat-card {
                background-color: white;
                padding: 10px;
                border-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #4CAF50;
            }
            .error-message {
                color: #f44336;
                margin-top: 15px;
            }
            .button-red {
                background-color: #f44336;
            }
            .button-red:hover {
                background-color: #d32f2f;
            }
            .refresh-button {
                background-color: #2196F3;
                margin-left: 10px;
            }
            .refresh-button:hover {
                background-color: #0b7dda;
            }
            #loading {
                display: none;
                margin-top: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Website Crawler Interface</h1>
            
            <form action="/start_crawl" method="post" id="crawlForm">
                <div class="form-group">
                    <label for="url">URL to crawl:</label>
                    <input type="url" id="url" name="url" placeholder="https://example.com" required>
                </div>
                
                <div class="form-group">
                    <label for="output_dir">Output Directory:</label>
                    <input type="text" id="output_dir" name="output_dir" value="./output">
                </div>
                
                <div class="form-group checkbox-group">
                    <input type="checkbox" id="js_rendering" name="js_rendering">
                    <label for="js_rendering" style="display:inline;">Enable JavaScript Rendering</label>
                </div>
                
                <button type="submit" {% if status.running %}disabled{% endif %}>Start Crawling</button>
                
                {% if status.running %}
                <form action="/stop_crawl" method="post" style="display:inline;">
                    <button type="submit" class="button-red">Stop Crawler</button>
                </form>
                {% endif %}
                
                <button type="button" id="refreshButton" class="refresh-button">Refresh Status</button>
            </form>
            
            <div id="loading">Loading...</div>
            
            <div class="status-panel">
                <h2>Crawler Status</h2>
                
                {% if status.running %}
                <p><strong>Status:</strong> <span style="color: green;">Running</span></p>
                <p><strong>URL:</strong> {{ status.url }}</p>
                <p><strong>Output Directory:</strong> {{ status.output_dir }}</p>
                <p><strong>Started:</strong> {{ status.start_time }}</p>
                
                <h3>Statistics</h3>
                <div class="stats-grid" id="statsGrid">
                    {% if status.stats %}
                        {% for category, data in status.stats.items() %}
                            {% if category != "timing" %}
                                {% for key, value in data.items() %}
                                <div class="stat-card">
                                    <div>{{ key.replace('_', ' ').title() }}</div>
                                    <div class="stat-value">{{ value }}</div>
                                </div>
                                {% endfor %}
                            {% endif %}
                        {% endfor %}
                    {% else %}
                    <p>No statistics available yet.</p>
                    {% endif %}
                </div>
                {% else %}
                <p><strong>Status:</strong> <span>Not Running</span></p>
                {% endif %}
            </div>
        </div>
        
        <script>
            document.getElementById('refreshButton').addEventListener('click', function() {
                const loading = document.getElementById('loading');
                loading.style.display = 'block';
                
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        loading.style.display = 'none';
                        window.location.reload();
                    })
                    .catch(error => {
                        loading.style.display = 'none';
                        console.error('Error:', error);
                    });
            });
        </script>
    </body>
    </html>
    """
    
    with open('templates/index.html', 'w') as f:
        f.write(index_html)

if __name__ == '__main__':
    create_templates()
    print("Web interface starting at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True) 