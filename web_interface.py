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
    print("DEBUG: web_interface.py index route accessed")
    app.logger.info("DEBUG: web_interface.py index route accessed")
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
    """Create template files if they don't exist"""
    # Comment out the entire function to prevent it from overriding our new templates
    """
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    index_path = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write('''
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
            button:disabled {
                background-color: #cccccc;
                cursor: not-allowed;
            }
            .button-red {
                background-color: #f44336;
            }
            .button-red:hover {
                background-color: #d32f2f;
            }
            .status-section {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }
            .status-item {
                margin-bottom: 10px;
            }
            .stats-container {
                display: flex;
                flex-wrap: wrap;
                margin-top: 15px;
            }
            .stat-box {
                background-color: #f5f5f5;
                border-radius: 4px;
                padding: 15px;
                margin-right: 15px;
                margin-bottom: 15px;
                min-width: 120px;
            }
            .stat-box h3 {
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 14px;
                color: #555;
            }
            .stat-box .value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            #status-controls {
                display: flex;
                align-items: center;
                margin-top: 15px;
            }
            .status-label {
                margin-right: 10px;
                font-weight: bold;
            }
            .status-value {
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            .status-not-running {
                background-color: #f44336;
                color: white;
            }
            .status-running {
                background-color: #4CAF50;
                color: white;
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
            </form>
            
            <div id="loading">
                <p>Processing... This may take a few seconds.</p>
            </div>
            
            <div class="status-section">
                <h2>Crawler Status</h2>
                
                <div id="status-controls">
                    <span class="status-label">Status:</span>
                    <span class="status-value {% if status.running %}status-running{% else %}status-not-running{% endif %}" id="status-indicator">
                        {% if status.running %}Running{% else %}Not Running{% endif %}
                    </span>
                    <button id="refresh-status" class="refresh-button">Refresh Status</button>
                </div>
                
                {% if status.running %}
                <div class="status-item">
                    <strong>URL:</strong> {{ status.url }}
                </div>
                <div class="status-item">
                    <strong>Output Directory:</strong> {{ status.output_dir }}
                </div>
                <div class="status-item">
                    <strong>Started:</strong> {{ status.start_time }}
                </div>
                
                <h3>Statistics</h3>
                <div class="stats-container" id="stats-container">
                    {% for key, value in status.stats.items() %}
                    <div class="stat-box">
                        <h3>{{ key|title }}</h3>
                        <div class="value">{{ value }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
        
        <script>
            document.getElementById('crawlForm').addEventListener('submit', function() {
                document.getElementById('loading').style.display = 'block';
            });
            
            document.getElementById('refresh-status').addEventListener('click', function() {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        // Update status indicator
                        const statusIndicator = document.getElementById('status-indicator');
                        statusIndicator.textContent = data.running ? 'Running' : 'Not Running';
                        statusIndicator.className = 'status-value ' + (data.running ? 'status-running' : 'status-not-running');
                        
                        // If running, update the stats
                        if (data.running) {
                            const statsContainer = document.getElementById('stats-container');
                            statsContainer.innerHTML = '';
                            
                            for (const [key, value] of Object.entries(data.stats)) {
                                const statBox = document.createElement('div');
                                statBox.className = 'stat-box';
                                statBox.innerHTML = `
                                    <h3>${key.charAt(0).toUpperCase() + key.slice(1)}</h3>
                                    <div class="value">${value}</div>
                                `;
                                statsContainer.appendChild(statBox);
                            }
                            
                            // Refresh the page if status changed
                            if (statusIndicator.textContent !== (data.running ? 'Running' : 'Not Running')) {
                                location.reload();
                            }
                        } else {
                            // Refresh the page if the crawler was previously running
                            if (statusIndicator.textContent === 'Running') {
                                location.reload();
                            }
                        }
                    })
                    .catch(error => console.error('Error fetching status:', error));
            });
        </script>
    </body>
    </html>
            ''')
    """

if __name__ == '__main__':
    # Comment out the create_templates call
    # create_templates()
    print("Web interface starting at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True) 