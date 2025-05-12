#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 4: pFaces Connection Test
This script tests the connection to the pFaces server
to see if that's where the delay occurs.
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

# Import RemoteSymbolicController
from RemoteSymbolicController import RemoteSymbolicController

# Server URLs
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
ROBOT_NAME = "DeepRacer1"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME

def main():
    print("\n=== Test 4: pFaces Connection Test ===")
    
    # Test connection to pFaces
    print("Connecting to pFaces server...")
    start_time = time.time()
    
    try:
        # Create a RemoteSymbolicController
        sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
        
        # Make a dummy request
        response = sym_control.get_controls("(0,0,0,0)", True)
        
        elapsed = time.time() - start_time
        print("Connection established in {:.2f} seconds".format(elapsed))
        print("Response: {}".format(response))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        print("Exception details:", e)
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
