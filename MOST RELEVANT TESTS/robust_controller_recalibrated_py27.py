#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import argparse
import traceback
import math
import socket

# Simple path setup - assumes running from deepracer-utils/examples/sym_control
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
examples_path = os.path.join(project_root, 'examples')
sym_control_path = os.path.join(examples_path, 'sym_control')

# Add all relevant paths to Python's module search path
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files
sys.path.insert(0, examples_path) # Examples
sys.path.insert(0, sym_control_path) # Symbolic controller

# Import modules
import RESTApiClient
import httplib2
try:
    from LocalizationServerInterface import LocalizationServerInterface
except ImportError as e:
    # Alternative approach: manual import
    import imp
    loc_server_path = os.path.join(src_path, 'LocalizationServerInterface.py')
    loc_module = imp.load_source('LocalizationServerInterface', loc_server_path)
    LocalizationServerInterface = loc_module.LocalizationServerInterface
from examples.sym_control.RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger

# Parse command line arguments
parser = argparse.ArgumentParser(description='DeepRacer Controller - Recalibrated Version (Python 2.7)')
parser.add_argument('--optitrack-server', default='192.168.1.194:12345', help='OptiTrack server IP:port')
parser.add_argument('--pfaces-server', default='192.168.1.144:12345', help='pFaces server IP:port')
parser.add_argument('--use-hardcoded', action='store_true', help='Use hardcoded values instead of real data')
parser.add_argument('--debug', action='store_true', help='Print debug information')
args = parser.parse_args()

# Configuration
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_URL = "http://{0}/OptiTrackRestServer".format(args.optitrack_server)
PFACES_SERVER_URL = "http://{0}/pFaces/REST/dictionary/DeepRacer1".format(args.pfaces_server)

# Hardcoded values from the working example
HARDCODED_OBSTACLE = "{0.5,1.5},{0.5,1.5},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
HARDCODED_TARGET = "{0.5,1.5},{0.5,1.5},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
HARDCODED_STATE = "0.0, 0.0, 0.0, 0.0"

# Theta range limits based on testing
THETA_MIN = -1.7  # Determined through testing
THETA_MAX = 1.7   # Determined through precise testing (values > 1.7 fail)

# Recalibration settings
RECALIBRATION_MAX = 3.2  # Original maximum theta value
RECALIBRATION_FACTOR = THETA_MAX / RECALIBRATION_MAX  # Scale factor for recalibration

# Initialize logger
logger = Logger()

def print_separator():
    """Print a separator line for better readability"""
    print("\n" + "-" * 50 + "\n")

def create_fixed_hyperrectangle(data, is_target=False):
    """Create a fixed hyperrectangle that uses real coordinates but follows the hardcoded format"""
    values = data.split(',')
    if len(values) >= 7:
        x = float(values[1].strip())
        y = float(values[2].strip())
        width = float(values[5].strip())
        height = float(values[6].strip())
        
        # Calculate bounding box
        x_min = x - width/2
        x_max = x + width/2
        y_min = y - height/2
        y_max = y + height/2
        
        # Create a hyperrectangle with real coordinates for first part, but hardcoded second part
        if is_target:
            return "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}|{{2.0,3.0}},{{2.0,3.0}},{{-3.2,3.2}},{{0.0,0.8}}".format(
                x_min, x_max, y_min, y_max)
        else:  # Obstacle
            return "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}|{{2.0,3.0}},{{2.0,3.0}},{{-3.2,3.2}},{{-2.1,2.1}}".format(
                x_min, x_max, y_min, y_max)
    else:
        return None

def recalibrate_theta(theta):
    """Recalibrate theta to map the range [-RECALIBRATION_MAX, RECALIBRATION_MAX] to [-THETA_MAX, THETA_MAX]"""
    # First, normalize to [-pi, pi]
    normalized = ((theta + math.pi) % (2 * math.pi)) - math.pi
    
    # Then, recalibrate to the acceptable range
    recalibrated = normalized * RECALIBRATION_FACTOR
    
    # Print recalibration info if there's a significant change
    if abs(recalibrated - normalized) > 0.001:
        print("Recalibrating theta: {0:.6f} -> {1:.6f}".format(normalized, recalibrated))
        print("(Original theta: {0:.6f})".format(theta))
    
    return recalibrated

# Track the last action to maintain driving direction consistency
last_action = None

def get_next_action(actions_list, state, logger):
    """Function to get next action from the list of actions, using DeepRacer-Utils approach"""
    global last_action
    
    if not actions_list or len(actions_list) == 0:
        raise ValueError("No actions received from controller")
    
    # Convert state string to list of floats if it's a string
    if isinstance(state, str):
        state = list(map(float, state.replace("(","").replace(")","").split(',')))
    
    new_actions_conc = []
    good_candidate_idx = 0  # Default to first action
    idx = 0
    
    for action_str in actions_list:
        # Skip empty actions
        if not action_str or action_str.strip() == "":
            logger.log("Skipping empty action at index {0}".format(idx))
            idx += 1
            continue
            
        # Clean up the action string and split it
        new_action = action_str.replace("(","").replace(")","").split(',')
        
        # Validate action format
        if len(new_action) != 2:
            logger.log("Invalid action format at index {0}: {1}".format(idx, action_str))
            idx += 1
            continue
        
        # Convert to floats
        try:
            new_action = [float(new_action[0]), float(new_action[1])]
            new_actions_conc.append(new_action)
            
            # Selection criterion from DeepRacer-Utils: first action with same direction as last action
            if last_action is not None:
                if (last_action[1] > 0 and new_action[1] > 0) or (last_action[1] < 0 and new_action[1] < 0):
                    good_candidate_idx = idx
                    break
        except ValueError:
            logger.log("Could not convert action to float: {0}".format(action_str))
        
        idx += 1
    
    # Check if we have any valid actions
    if not new_actions_conc:
        raise ValueError("No valid actions found")
    
    # Store the selected action for next time
    selected_action = new_actions_conc[min(good_candidate_idx, len(new_actions_conc)-1)]
    if selected_action:
        last_action = selected_action[:]  # Make a copy in Python 2.7
    else:
        last_action = None
        
    return selected_action

def check_pfaces_server(url):
    """Check if the pFaces server is running and accessible"""
    try:
        http = httplib2.Http(timeout=5)
        response, content = http.request(url, method="GET")
        if response.status == 200:
            print("✓ Successfully connected to pFaces server")
            return True
        else:
            print("⚠ pFaces server returned status code: {0}".format(response.status))
            return False
    except socket.timeout:
        print("✗ Connection to pFaces server timed out")
        print("\nWARNING: The controller will continue but may fail when calling pFaces.")
        return False
    except Exception as e:
        print("✗ Failed to connect to pFaces server: {0}".format(str(e)))
        print("\nWARNING: The controller will continue but may fail when calling pFaces.")
        return False

def main():
    """Main function"""
    print("\n=== DeepRacer Controller - Recalibrated Version (Python 2.7) ===")
    print("This controller recalibrates theta values to work with the pFaces server")
    
    print_separator()
    print("CONFIGURATION")
    print("OptiTrack server: {0}".format(LOCALIZATION_SERVER_URL))
    print("pFaces server: {0}".format(PFACES_SERVER_URL))
    print("Original theta range: [-{0}, {0}]".format(RECALIBRATION_MAX))
    print("Recalibrated theta range: [{0}, {1}]".format(THETA_MIN, THETA_MAX))
    print("Recalibration factor: {0}".format(RECALIBRATION_FACTOR))
    print("Debug mode: {0}".format('Enabled' if args.debug else 'Disabled'))
    
    # Check if pFaces server is running
    if not check_pfaces_server(PFACES_SERVER_URL):
        print_separator()
        print("ERROR: pFaces server is not running or not accessible")
        print("Please start the pFaces server and try again")
        return
    
    try:
        # Get values to use (either hardcoded or real)
        if args.use_hardcoded:
            print("\nUsing hardcoded values:")
            obstacles_str = HARDCODED_OBSTACLE
            target_str = HARDCODED_TARGET
            state_str = HARDCODED_STATE
            print("Obstacles: {0}".format(obstacles_str))
            print("Target: {0}".format(target_str))
            print("State: {0}".format(state_str))
        else:
            print("\nGetting real-time data from OptiTrack...")
            try:
                # Use a shorter timeout for OptiTrack to avoid long waits
                import RESTApiClient
                # Save original timeout
                original_timeout = RESTApiClient.RESTApiClient.timeout if hasattr(RESTApiClient.RESTApiClient, 'timeout') else 3
                
                # Set a shorter timeout temporarily
                RESTApiClient.RESTApiClient.timeout = 1
                
                print("Using shortened timeout (1 second) for faster response")
                localization_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
                raw_data = localization_server.rest_client.restGETjson()
                
                # Restore original timeout
                RESTApiClient.RESTApiClient.timeout = original_timeout
                
                if not raw_data:
                    print("Error: OptiTrack server returned empty data")
                    print("Using hardcoded values instead")
                    obstacles_str = HARDCODED_OBSTACLE
                    target_str = HARDCODED_TARGET
                    state_str = HARDCODED_STATE
                    raise Exception("Fast fallback to hardcoded values")
                    
                # Check for required objects
                required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
                missing_objects = []
                
                for obj in required_objects:
                    if obj not in raw_data or raw_data[obj] == "untracked":
                        missing_objects.append(obj)
                
                if missing_objects:
                    print("Error: Required objects missing: {0}".format(", ".join(missing_objects)))
                    return
                
                # Process DeepRacer1 data
                deepracer_data = raw_data["DeepRacer1"]
                values = deepracer_data.split(',')
                if len(values) >= 5:
                    x = float(values[1].strip())
                    y = float(values[2].strip())
                    z = float(values[3].strip())
                    theta = float(values[4].strip())
                    
                    # Recalibrate theta to be within the acceptable range
                    recalibrated_theta = recalibrate_theta(theta)
                    
                    state_str = "{0:.6f}, {1:.6f}, {2:.6f}, {3:.6f}".format(x, y, z, recalibrated_theta)
                    print("DeepRacer state: {0}".format(state_str))
                else:
                    print("Error: Invalid DeepRacer1 data format")
                    return
                
                # Create fixed hyperrectangles
                target_str = create_fixed_hyperrectangle(raw_data["Target4"], is_target=True)
                obstacles_str = create_fixed_hyperrectangle(raw_data["Obstacle4"], is_target=False)
                
                if not target_str or not obstacles_str:
                    print("Error: Could not create hyperrectangles")
                    return
                    
                if args.debug:
                    print("Target hyperrectangle: {0}".format(target_str))
                    print("Obstacle hyperrectangle: {0}".format(obstacles_str))
                    
            except Exception as e:
                if "Fast fallback" not in str(e):
                    print("Error getting OptiTrack data: {0}".format(str(e)))
                    print("Using hardcoded values instead")
                obstacles_str = HARDCODED_OBSTACLE
                target_str = HARDCODED_TARGET
                state_str = HARDCODED_STATE
        
        # Now follow the exact pattern of synth_and_get.py
        print("\nCreating symbolic controller...")
        try:
            symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)
        except Exception as e:
            if "mode" in str(e):
                print_separator()
                print("ERROR: Could not get server mode")
                print("Please restart the pFaces server and try again")
                return
            else:
                raise
        
        print("Requesting synthesis...")
        try:
            symbolic_controller.synthesize_controller(obstacles_str, target_str, is_last_req=True)
        except Exception as e:
            if "mode" in str(e):
                print_separator()
                print("ERROR: Server mode error during synthesis")
                print("Please restart the pFaces server and try again")
                return
            elif "connection" in str(e).lower():
                print_separator()
                print("ERROR: Connection error during synthesis")
                print("Please check that the pFaces server is running and try again")
                return
            else:
                raise
        
        print("Waiting briefly for synthesis...")
        time.sleep(1)
        
        print("Creating new controller for control request...")
        try:
            symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)  # Create a new controller
        except Exception as e:
            if "mode" in str(e):
                print_separator()
                print("ERROR: Could not get server mode")
                print("Please restart the pFaces server and try again")
                return
            else:
                raise
        
        print("Requesting control for state: {0}".format(state_str))
        try:
            action_str = symbolic_controller.get_controls(state_str, is_last_request=True)
        except KeyError as e:
            if "is_control_ready" in str(e):
                print_separator()
                print("ERROR: Server did not return control ready status")
                print("This can happen when the theta value is outside the acceptable range")
                print("Current recalibrated theta value: {0:.6f}".format(float(state_str.split(',')[3])))
                print("Please reorient the DeepRacer to have a theta value closer to 0")
                return
            else:
                raise
        except Exception as e:
            if "connection" in str(e).lower():
                print_separator()
                print("ERROR: Connection error during control request")
                print("Please check that the pFaces server is running and try again")
                return
            else:
                raise
        
        print("Received actions: {0}".format(action_str))
        
        # Check if we got a valid action
        if not action_str or action_str.strip() == "":
            print_separator()
            print("ERROR: Received empty action from server")
            print("This can happen when the state is outside the controller's domain")
            print("Please try again with a different state or orientation")
            return
        
        # Parse the actions
        actions_list = action_str.replace(" ", "").split('|')
        if not actions_list:
            print("No valid actions found")
            return
            
        # Get the next action using the DeepRacer-Utils approach
        action = get_next_action(actions_list, state_str, logger)
            
        print_separator()
        print("FINAL RESULT")
        print("Selected action: steering = {0}, speed = {1}".format(action[0], action[1]))
            
    except Exception as e:
        print_separator()
        print("UNEXPECTED ERROR: {0}".format(str(e)))
        if args.debug:
            traceback.print_exc()

if __name__ == "__main__":
    main()
