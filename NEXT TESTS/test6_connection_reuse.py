#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 6: Connection Reuse Test
This script tests whether reusing the same HTTP connection
causes delays in subsequent requests.
"""

import sys
import os
import json
import time
import httplib2

# Simple path setup
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

# Server URLs
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"

def main():
    print("\n=== Test 6: Connection Reuse Test ===")
    
    # Create a single HTTP connection to be reused
    http = httplib2.Http(timeout=180)  # 3 minute timeout
    
    # First request
    print("Making first request...")
    start_time = time.time()
    
    try:
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        
        elapsed = time.time() - start_time
        print("First request completed in {:.2f} seconds".format(elapsed))
        
        if response.status == 200:
            print("Success! HTTP Status: {}".format(response.status))
            
            # Parse JSON response
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
            print("Total objects: {}".format(len(data)))
        else:
            print("Error: HTTP Status {}".format(response.status))
        
        # Second request using the same connection
        print("\nMaking second request (reusing connection)...")
        start_time = time.time()
        
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        
        elapsed = time.time() - start_time
        print("Second request completed in {:.2f} seconds".format(elapsed))
        
        if response.status == 200:
            print("Success! HTTP Status: {}".format(response.status))
            
            # Parse JSON response
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
            print("Total objects: {}".format(len(data)))
        else:
            print("Error: HTTP Status {}".format(response.status))
        
        # Third request using the same connection
        print("\nMaking third request (reusing connection)...")
        start_time = time.time()
        
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        
        elapsed = time.time() - start_time
        print("Third request completed in {:.2f} seconds".format(elapsed))
        
        if response.status == 200:
            print("Success! HTTP Status: {}".format(response.status))
            
            # Parse JSON response
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
            print("Total objects: {}".format(len(data)))
        else:
            print("Error: HTTP Status {}".format(response.status))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
