#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test 7: Full Controller Sequence Test
This script tests the full controller sequence similar to the robust controller
but with timing information at each step.
"""

import sys
import os
import json
import time
import math

# Simple path setup
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

# Import necessary modules
from LocalizationServerInterface import LocalizationServerInterface
from RemoteSymbolicController import RemoteSymbolicController

# Constants
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
ROBOT_NAME = "DeepRacer1"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME
THETA_MIN = -1.7
THETA_MAX = 1.7

def normalize_theta(theta):
    # Normalize theta to be within the acceptable range
    normalized = ((theta + math.pi) % (2 * math.pi)) - math.pi
    if normalized > THETA_MAX:
        return THETA_MAX
    elif normalized < THETA_MIN:
        return THETA_MIN
    return normalized

def stack_hrs(hrList):
    ret_str = ""
    idx = 0
    l = len(hrList)
    for name_hr in hrList:
        ret_str += name_hr[1]
        if idx < l-1:
             ret_str += "|"
        idx += 1
    return ret_str

def fix_hyperrectangle_format(hr_str):
    """Fix the hyperrectangle format to include the hardcoded second part"""
    parts = hr_str.split('|')
    first_part = parts[0]
    
    # Extract theta and velocity ranges from the first part
    components = first_part.split('},')
    if len(components) >= 4:
        theta_v_part = components[2] + '},' + components[3]
        
        # For targets
        if "{0.0,0.8}" in theta_v_part:
            return first_part + "|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
        # For obstacles
        else:
            return first_part + "|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
    
    return hr_str

def main():
    print("\n=== Test 7: Full Controller Sequence Test ===")
    
    try:
        # Step 1: Connect to OptiTrack
        print("Step 1: Connecting to OptiTrack server...")
        start_time = time.time()
        
        loc_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
        
        elapsed = time.time() - start_time
        print("OptiTrack connection established in {:.2f} seconds".format(elapsed))
        
        # Step 2: Get rigid body state
        print("\nStep 2: Getting rigid body state...")
        start_time = time.time()
        
        state = loc_server.getRigidBodyState("DeepRacer1")
        
        elapsed = time.time() - start_time
        print("Rigid body state retrieved in {:.2f} seconds".format(elapsed))
        print("DeepRacer1 state: {}".format(state))
        
        # Step 3: Get hyperrectangles
        print("\nStep 3: Getting hyperrectangles...")
        start_time = time.time()
        
        hrListTar = loc_server.get_hyper_rec_str("Target")
        hrListObs = loc_server.get_hyper_rec_str("Obstacle")
        
        elapsed = time.time() - start_time
        print("Hyperrectangles retrieved in {:.2f} seconds".format(elapsed))
        
        # Step 4: Format hyperrectangles
        print("\nStep 4: Formatting hyperrectangles...")
        start_time = time.time()
        
        target_str = stack_hrs(hrListTar)
        obstacles_str = stack_hrs(hrListObs)
        
        # Fix the hyperrectangle format
        target_str = fix_hyperrectangle_format(target_str)
        obstacles_str = fix_hyperrectangle_format(obstacles_str)
        
        elapsed = time.time() - start_time
        print("Hyperrectangles formatted in {:.2f} seconds".format(elapsed))
        print("Target: {}".format(target_str))
        print("Obstacles: {}".format(obstacles_str))
        
        # Step 5: Create RemoteSymbolicController
        print("\nStep 5: Creating RemoteSymbolicController...")
        start_time = time.time()
        
        sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
        
        elapsed = time.time() - start_time
        print("RemoteSymbolicController created in {:.2f} seconds".format(elapsed))
        
        # Step 6: Synthesize controller
        print("\nStep 6: Synthesizing controller...")
        start_time = time.time()
        
        result = sym_control.synthesize_controller(obstacles_str, target_str)
        
        elapsed = time.time() - start_time
        print("Controller synthesized in {:.2f} seconds".format(elapsed))
        print("Result: {}".format(result))
        
        # Step 7: Wait a bit for synthesis to complete
        print("\nStep 7: Waiting for 1 second...")
        time.sleep(1)
        
        # Step 8: Create a new controller instance
        print("\nStep 8: Creating new RemoteSymbolicController...")
        start_time = time.time()
        
        new_sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
        
        elapsed = time.time() - start_time
        print("New RemoteSymbolicController created in {:.2f} seconds".format(elapsed))
        
        # Step 9: Normalize theta
        print("\nStep 9: Normalizing theta...")
        start_time = time.time()
        
        # Parse state
        state_values = state.split(',')
        if len(state_values) >= 4:
            original_theta = float(state_values[3])
            normalized_theta = normalize_theta(original_theta)
            
            if original_theta != normalized_theta:
                print("Theta normalized from {:.2f} to {:.2f}".format(original_theta, normalized_theta))
                state_values[3] = str(normalized_theta)
                state = ','.join(state_values)
        
        elapsed = time.time() - start_time
        print("Theta normalized in {:.2f} seconds".format(elapsed))
        
        # Step 10: Get controls
        print("\nStep 10: Getting controls...")
        start_time = time.time()
        
        # Format state
        s_send = state.replace('[','(').replace(']',')')
        
        # Get controls
        controls = new_sym_control.get_controls(s_send, True)
        
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
