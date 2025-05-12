#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import argparse
import traceback

# Simple path setup - assumes running from deepracer-utils/examples/sym_control
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
examples_path = os.path.join(project_root, 'examples')
sym_control_path = os.path.join(examples_path, 'sym_control')

print("Project root: " + project_root)
print("Source path: " + src_path)

# Add all relevant paths to Python's module search path
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files
sys.path.insert(0, examples_path) # Examples
sys.path.insert(0, sym_control_path) # Symbolic controller

print("Python path now includes:")
print(" - " + project_root)
print(" - " + src_path)

# Before import, let's check if the file exists
loc_server_path = os.path.join(src_path, 'LocalizationServerInterface.py')
print("Checking if file exists: " + loc_server_path)
print("File exists: " + str(os.path.exists(loc_server_path)))

# List what's in the src directory
print("\nContents of src directory:")
for item in os.listdir(src_path):
    print(" - " + item)

# Force import using full path
sys.path.insert(0, os.path.dirname(loc_server_path))

# Now import modules
import RESTApiClient
import httplib2
# Try a direct import
try:
    from LocalizationServerInterface import LocalizationServerInterface
    print("Successfully imported LocalizationServerInterface")
except ImportError as e:
    print("ERROR importing LocalizationServerInterface: " + str(e))
    # Alternative approach: manual import
    print("Trying manual import...")
    import imp
    loc_module = imp.load_source('LocalizationServerInterface', loc_server_path)
    LocalizationServerInterface = loc_module.LocalizationServerInterface
    print("Manual import successful")
except Exception as e:
    print("Unexpected error importing: " + str(e))
    traceback.print_exc()
from examples.sym_control.RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger

# Parse command line arguments
parser = argparse.ArgumentParser(description='DeepRacer Controller - No Dummy Data (Python 2.7 Version)')
parser.add_argument('--optitrack-server', default='192.168.1.194:12345', help='OptiTrack server IP:port')
parser.add_argument('--pfaces-server', default='192.168.1.144:12345', help='pFaces server IP:port')
parser.add_argument('--debug', action='store_true', help='Print debug information')
args = parser.parse_args()

# Configuration
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_URL = "http://{0}/OptiTrackRestServer".format(args.optitrack_server)
PFACES_SERVER_URL = "http://{0}/pFaces/REST/dictionary/DeepRacer1".format(args.pfaces_server)

# Initialize logger
logger = Logger()

def print_separator():
    """Print a separator line for better readability"""
    print("\n" + "-" * 50 + "\n")

def calculate_hyperrectangle(data, is_target=False):
    """Calculate hyperrectangle from object data, using real coordinates but working theta/velocity values"""
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
        
        # Create a single hyperrectangle based on real coordinates
        if is_target:
            single_hr = "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}".format(
                x_min, x_max, y_min, y_max)
        else:  # Obstacle
            single_hr = "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}".format(
                x_min, x_max, y_min, y_max)
            
        # Duplicate it with | separator to match the working format
        return "{0}|{0}".format(single_hr)
    else:
        return None

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

def test_pfaces_connection(url):
    """Test connection to pFaces server using httplib2 instead of requests"""
    try:
        http = httplib2.Http(timeout=5)
        response, content = http.request(url, method="GET")
        if response.status == 200:
            print("✓ Successfully connected to pFaces server")
            return True
        else:
            print("⚠ pFaces server returned status code: {0}".format(response.status))
            return False
    except Exception as e:
        print("✗ Failed to connect to pFaces server: {0}".format(str(e)))
        print("\nWARNING: The controller will continue but may fail when calling pFaces.")
        return False

def main():
    """Main function"""
    print("\n=== DeepRacer Controller - No Dummy Data (Python 2.7 Version) ===")
    print("This script gets real-time data from the OptiTrack server")
    print("and sends it to the pFaces server to get control actions.")
    
    print_separator()
    print("INITIALIZATION")
    print("OptiTrack server: {0}".format(LOCALIZATION_SERVER_URL))
    print("pFaces server: {0}".format(PFACES_SERVER_URL))
    
    # Test OptiTrack connection
    print("\nConnecting to OptiTrack server...")
    try:
        localization_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
        # Test if we can get data
        test_data = localization_server.rest_client.restGETjson()
        if test_data:
            print("✓ Successfully connected to OptiTrack server")
        else:
            print("⚠ Connected to OptiTrack but received empty data")
            
        # Test pFaces connection
        print("\nConnecting to pFaces server...")
        test_pfaces_connection(PFACES_SERVER_URL)
    
        print_separator()
        print("GETTING DATA FROM OPTITRACK")
        
        # Get raw data from OptiTrack server
        print("Getting raw data from OptiTrack server...")
        raw_data = localization_server.rest_client.restGETjson()
        
        # Check for required objects
        required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
        missing_objects = []
        
        for obj in required_objects:
            if obj not in raw_data or raw_data[obj] == "untracked":
                missing_objects.append(obj)
        
        if missing_objects:
            raise ValueError("Required objects are missing or untracked: {0}".format(", ".join(missing_objects)))
        
        # Process DeepRacer1 data
        print("\nProcessing DeepRacer1 data...")
        deepracer_data = raw_data["DeepRacer1"]
        values = deepracer_data.split(',')
        if len(values) >= 5:
            state = [float(values[1].strip()), float(values[2].strip()), 
                    float(values[3].strip()), float(values[4].strip())]
            print("DeepRacer state: {0}".format(state))
        else:
            raise ValueError("Invalid DeepRacer1 data format: {0}".format(deepracer_data))
        
        # Process Target4 data
        print("\nProcessing Target4 data...")
        target_hr = calculate_hyperrectangle(raw_data["Target4"], is_target=True)
        if not target_hr:
            raise ValueError("Invalid Target4 data format: {0}".format(raw_data['Target4']))
        print("Target hyperrectangle: {0}".format(target_hr))
        
        # Process Obstacle4 data
        print("\nProcessing Obstacle4 data...")
        obstacle_hr = calculate_hyperrectangle(raw_data["Obstacle4"], is_target=False)
        if not obstacle_hr:
            raise ValueError("Invalid Obstacle4 data format: {0}".format(raw_data['Obstacle4']))
        print("Obstacle hyperrectangle: {0}".format(obstacle_hr))
        
        # Check if already in target
        target_vals = target_hr.replace('{','').replace('}','').split(',')
        if (state[0] >= float(target_vals[0]) and state[0] <= float(target_vals[1])) and \
            (state[1] >= float(target_vals[2]) and state[1] <= float(target_vals[3])):
            print("\nAlready in the target set. Stopping.")
            return
        
        print("\n--------------------------------------------------\n")
        print("CALLING PFACES SERVER")
        
        # Format the request data clearly
        formatted_state = "{0:.6f}, {1:.6f}, {2:.6f}, {3:.6f}".format(
            state[0], state[1], state[2], state[3])
        
        print("\n=== REQUEST DATA ===\n")
        print("STATE:\n{0}".format(formatted_state))
        print("\nTARGET:\n{0}".format(target_hr))
        print("\nOBSTACLES:\n{0}".format(obstacle_hr))
        print("\n=== END REQUEST DATA ===\n")
        
        print("1. Requesting synthesis...")
        symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)
        synthesis_response = symbolic_controller.synthesize_controller(obstacle_hr, target_hr, is_last_req=True)
        print("   Synthesis response: {0}".format(synthesis_response))
        
        print("2. Waiting briefly for synthesis...")
        time.sleep(1)
        
        print("3. Creating new connection for control request...")
        symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)  # Create a new connection
        print("4. Requesting control for state: {0}".format(formatted_state))
        actions = symbolic_controller.get_controls(formatted_state, is_last_request=True)
        print("4. Received response: {0}".format(actions))
        
        # Validate and process the response
        if not actions or actions.strip() == "":
            raise ValueError("Empty response from pFaces server")
        
        # Clean up the response and split it into actions
        actions = actions.replace(" ", "")
        actions_list = actions.split('|')
        
        print("5. Split response into {0} potential actions".format(len(actions_list)))
        
        # Get the next action - pass the state to maintain direction consistency
        action = get_next_action(actions_list, formatted_state, logger)
        
        print_separator()
        print("FINAL RESULT")
        print("Selected action: {0}".format(action))
            
    except ValueError as e:
        print_separator()
        print("ERROR: {0}".format(str(e)))
        print("The controller cannot proceed without valid data.")
        print("Please ensure that:")
        print("1. The OptiTrack server is running and accessible")
        print("2. The required objects (DeepRacer1, Obstacle4, Target4) are being tracked")
        print("3. The pFaces server is running and responding correctly")
        
    except Exception as e:
        print_separator()
        print("UNEXPECTED ERROR: {0}".format(str(e)))
        if args.debug:
            traceback.print_exc()

if __name__ == "__main__":
    main()