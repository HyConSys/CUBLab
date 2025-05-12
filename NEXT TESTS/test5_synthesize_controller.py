#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 5: Synthesize Controller Test
This script tests the controller synthesis step
to see if that's where the delay occurs.
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

# Import RemoteSymbolicController
from RemoteSymbolicController import RemoteSymbolicController

# Server URLs
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
ROBOT_NAME = "DeepRacer1"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME

def main():
    print("\n=== Test 5: Synthesize Controller Test ===")
    
    # Test controller synthesis
    print("Creating RemoteSymbolicController...")
    start_time = time.time()
    
    try:
        # Create a RemoteSymbolicController
        sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
        
        elapsed = time.time() - start_time
        print("Controller created in {:.2f} seconds".format(elapsed))
        
        # Define hyperrectangles with the correct format
        obstacles_str = "{1.0,1.5},{1.0,1.5},{-3.2,3.2},{-2.1,2.1}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
        target_str = "{4.0,4.5},{4.0,4.5},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
        
        # Synthesize controller
        print("\nSynthesizing controller...")
        start_time = time.time()
        
        result = sym_control.synthesize_controller(obstacles_str, target_str)
        
        elapsed = time.time() - start_time
        print("Controller synthesized in {:.2f} seconds".format(elapsed))
        print("Result: {}".format(result))
        
        # Wait a bit for synthesis to complete
        print("\nWaiting for 1 second...")
        time.sleep(1)
        
        # Get controls
        print("\nGetting controls...")
        start_time = time.time()
        
        # Create a new controller instance (as in synth_and_test)
        new_sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
        
        # Get controls
        controls = new_sym_control.get_controls("(2.0,2.0,0.0,0.5)", True)
        
        elapsed = time.time() - start_time
        print("Controls retrieved in {:.2f} seconds".format(elapsed))
        print("Controls: {}".format(controls))
            
    except Exception as e:
        elapsed = time.time() - start_time
        print("Error after {:.2f} seconds: {}".format(elapsed, str(e)))
        print("Exception details:", e)
        
    print("\nTest completed.")

if __name__ == "__main__":
    main()
