#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 3: LocalizationServerInterface Test
This script tests the connection using the LocalizationServerInterface class
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

# Import LocalizationServerInterface
from LocalizationServerInterface import LocalizationServerInterface

# Server URLs
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"

def main():
    print("\n=== Test 3: LocalizationServerInterface Test ===")
    
    # Test connection to OptiTrack using LocalizationServerInterface
    print("Connecting to OptiTrack server using LocalizationServerInterface...")
    start_time = time.time()
    
    try:
        # Create a LocalizationServerInterface
        loc_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
        
        # Get rigid body state
        state = loc_server.getRigidBodyState("DeepRacer1")
        
        elapsed = time.time() - start_time
        print("Connection established in {:.2f} seconds".format(elapsed))
        print("DeepRacer1 state: {}".format(state))
        
        # Get hyperrectangles
        print("\nGetting hyperrectangles...")
        start_time = time.time()
        
        targets = loc_server.get_hyper_rec_str("Target")
        
        elapsed = time.time() - start_time
        print("Hyperrectangles retrieved in {:.2f} seconds".format(elapsed))
        print("Targets: {}".format(targets))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        print("Exception details:", e)
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
