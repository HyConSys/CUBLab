#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 1: Basic Connection Test
This script tests the most basic connection to the OptiTrack server
with minimal code - similar to synth_and_test.
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
    print("\n=== Test 1: Basic Connection Test ===")
    
    # Test connection to OptiTrack
    print("Connecting to OptiTrack server...")
    start_time = time.time()
    
    try:
        # Create a new HTTP connection
        http = httplib2.Http(timeout=180)  # 3 minute timeout
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        
        elapsed = time.time() - start_time
        print("Connection established in {:.2f} seconds".format(elapsed))
        
        if response.status == 200:
            print("Success! HTTP Status: {}".format(response.status))
            
            # Parse JSON response
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
            
            # Print first few items
            print("\nFirst few tracked objects:")
            count = 0
            for key, value in data.items():
                print("  {}: {}".format(key, value))
                count += 1
                if count >= 3:
                    break
            
            print("\nTotal objects: {}".format(len(data)))
        else:
            print("Error: HTTP Status {}".format(response.status))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
