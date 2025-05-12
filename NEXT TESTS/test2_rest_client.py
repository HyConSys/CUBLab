#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 2: RESTApiClient Test
This script tests the connection using the RESTApiClient class
to see if that introduces any delay.
"""

import sys
import os
import json
import time

# Simple path setup
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

# Import RESTApiClient
from RESTApiClient import RESTApiClient

# Server URLs
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"

def main():
    print("\n=== Test 2: RESTApiClient Test ===")
    
    # Test connection to OptiTrack using RESTApiClient
    print("Connecting to OptiTrack server using RESTApiClient...")
    start_time = time.time()
    
    try:
        # Create a RESTApiClient
        rest_client = RESTApiClient(LOCALIZATION_SERVER_URL)
        
        # Make a request
        data = rest_client.restGETjson()
        
        elapsed = time.time() - start_time
        print("Connection established in {:.2f} seconds".format(elapsed))
        
        # Print first few items
        print("\nFirst few tracked objects:")
        count = 0
        for key, value in data.items():
            print("  {}: {}".format(key, value))
            count += 1
            if count >= 3:
                break
        
        print("\nTotal objects: {}".format(len(data)))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        print("Exception details:", e)
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
