#!/usr/bin/env python3
"""
Script to start the new web crawler interface and ensure the old one is stopped.
This version works better on macOS which has stricter permission requirements.
"""
import os
import subprocess
import time
import sys
import signal
import glob

def find_and_kill_processes():
    """Find and kill Python processes related to our web servers using a more Mac-friendly approach"""
    print("Stopping any running web servers...")
    
    # Use pgrep to find Python processes running our scripts
    try:
        # Find all python processes with our target scripts in the command line
        pgrep_cmd = ["pgrep", "-fl", "python"]
        result = subprocess.run(pgrep_cmd, capture_output=True, text=True)
        
        for line in result.stdout.splitlines():
            if "web_interface" in line or "serverless_api" in line:
                try:
                    pid = int(line.split()[0])
                    print(f"Found process: {line}")
                    print(f"Killing process {pid}...")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)  # Give it time to terminate
                    
                    # Check if it's still running
                    try:
                        os.kill(pid, 0)  # This will raise an error if process doesn't exist
                        print(f"Process {pid} is still running, force killing...")
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        # Process is gone
                        pass
                    
                except (ValueError, IndexError, ProcessLookupError) as e:
                    print(f"Error processing line '{line}': {e}")
    except Exception as e:
        print(f"Error finding processes: {e}")
        print("If you experience issues, manually kill Python processes with:")
        print("  pkill -f 'python.*web_interface|python.*serverless'")
    
    # Wait a moment to ensure ports are released
    time.sleep(2)

def clear_cache():
    """Clear cache directories"""
    cache_dirs = [
        os.path.join(os.getcwd(), '.cache'),
        os.path.join(os.getcwd(), '__pycache__'),
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            print(f"Clearing cache directory: {cache_dir}")
            try:
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
            except Exception as e:
                print(f"Error clearing cache: {e}")
    
    # Also clear any __pycache__ directories
    try:
        for pycache_dir in glob.glob('**/__pycache__', recursive=True):
            if os.path.isdir(pycache_dir):
                print(f"Clearing Python cache: {pycache_dir}")
                for item in os.listdir(pycache_dir):
                    item_path = os.path.join(pycache_dir, item)
                    if os.path.isfile(item_path):
                        try:
                            os.unlink(item_path)
                        except:
                            pass
    except Exception as e:
        print(f"Error clearing Python cache: {e}")

def browser_cache_instructions():
    """Print instructions for clearing browser cache"""
    print("\n" + "="*80)
    print("IMPORTANT: BROWSER CACHE INSTRUCTIONS")
    print("="*80)
    print("To ensure you see the new interface, please:")
    print("1. Open a new browser window or tab")
    print("2. Clear your browser cache:")
    print("   • Chrome/Edge: Press Cmd+Shift+Delete → Check 'Cached images and files' → Clear data")
    print("   • Firefox: Press Cmd+Shift+Delete → Check 'Cache' → Clear")
    print("   • Safari: Press Option+Cmd+E")
    print("3. After the server starts, go to http://127.0.0.1:5050")
    print("4. If you still see the old interface or error, do a hard refresh:")
    print("   • Press Cmd+Shift+R")
    print("="*80 + "\n")

def start_new_server():
    """Start the serverless API"""
    print("\nStarting the new web interface...")
    print("="*80)
    print("The new interface will be available at: http://127.0.0.1:5050")
    print("="*80)
    
    # Use subprocess instead of exec to avoid permission issues
    try:
        # Run the server process
        server_cmd = [sys.executable, "serverless_api.py"]
        print(f"Running command: {' '.join(server_cmd)}")
        subprocess.run(server_cmd)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTry running it manually with:")
        print("  python serverless_api.py")

def main():
    print("\n" + "="*80)
    print("STARTING THE WEB CRAWLER INTERFACE")
    print("="*80)
    print("This script will ensure only the new web interface design is running.\n")
    
    # Kill any existing servers
    find_and_kill_processes()
    
    # Clear cache
    clear_cache()
    
    # Print browser cache instructions
    browser_cache_instructions()
    
    # Start new server
    start_new_server()

if __name__ == "__main__":
    main() 