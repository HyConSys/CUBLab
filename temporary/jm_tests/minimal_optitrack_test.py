#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import traceback
import httplib2

# Simple path setup - assumes running from deepracer-utils/examples/sym_control
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files

# Configuration
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
LOCALIZATION_SERVER_URL = "http://{0}/OptiTrackRestServer".format(LOCALIZATION_SERVER_IPPORT)

def test_optitrack_connection():
    """Test connection to OptiTrack server using the same method as robust_controller_py27.py"""
    print("\n=== Testing OptiTrack Connection (Minimal Version) ===")
    print("URL: " + LOCALIZATION_SERVER_URL)
    
    try:
        print("Creating HTTP connection...")
        http = httplib2.Http(timeout=30)
        
        print("Sending request to OptiTrack server...")
        start_time = time.time()
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        elapsed = time.time() - start_time
        
        print("Response received in {0:.2f} seconds".format(elapsed))
        print("HTTP Status: " + str(response.status))
        
        if response.status != 200:
            print("Error: HTTP status {0}".format(response.status))
            return False
        
        # Parse JSON response
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            data = json.loads(content)
            print("Successfully parsed JSON response")
            
            # Print objects found
            objects = []
            for key in data:
                if data[key] != "untracked":
                    objects.append(key)
            
            if objects:
                print("Found {0} tracked objects: {1}".format(len(objects), ", ".join(objects)))
            else:
                print("No tracked objects found")
            
            # Print sample of response
            print("\nResponse sample: " + str(content)[:200] + "...")
            
            return True
            
        except ValueError as e:
            print("JSON parsing error: " + str(e))
            print("Response content: " + str(content)[:100] + "...")
            return False
            
    except Exception as e:
        print("Error connecting to OptiTrack server: " + str(e))
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_optitrack_connection()
