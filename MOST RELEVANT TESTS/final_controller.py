import sys
import os
import json
import time
import argparse
import traceback

# Get path to project root (deepracer-utils-github)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)  # so 'examples' is found
sys.path.insert(0, os.path.join(project_root, 'src'))  # so 'RESTApiClient' is found

from LocalizationServerInterface import LocalizationServerInterface
from examples.sym_control.RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger
import RESTApiClient

# Parse command line arguments
parser = argparse.ArgumentParser(description='DeepRacer Controller - No Dummy Data')
parser.add_argument('--optitrack-server', default='192.168.1.194:12345', help='OptiTrack server IP:port')
parser.add_argument('--pfaces-server', default='192.168.1.144:12345', help='pFaces server IP:port')
parser.add_argument('--debug', action='store_true', help='Print debug information')
args = parser.parse_args()

# Configuration
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_URL = f"http://{args.optitrack_server}/OptiTrackRestServer"
PFACES_SERVER_URL = f"http://{args.pfaces_server}/pFaces/REST/dictionary/DeepRacer1"

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
            single_hr = f"{{{x_min:.4f},{x_max:.4f}}},{{{y_min:.4f},{y_max:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}"
        else:  # Obstacle
            single_hr = f"{{{x_min:.4f},{x_max:.4f}}},{{{y_min:.4f},{y_max:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}"
            
        # Duplicate it with | separator to match the working format
        return f"{single_hr}|{single_hr}"
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
            logger.log(f"Skipping empty action at index {idx}")
            idx += 1
            continue
            
        # Clean up the action string and split it
        new_action = action_str.replace("(","").replace(")","").split(',')
        
        # Validate action format
        if len(new_action) != 2:
            logger.log(f"Invalid action format at index {idx}: {action_str}")
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
            logger.log(f"Could not convert action to float: {action_str}")
        
        idx += 1
    
    # Check if we have any valid actions
    if not new_actions_conc:
        raise ValueError("No valid actions found")
    
    # Store the selected action for next time
    selected_action = new_actions_conc[min(good_candidate_idx, len(new_actions_conc)-1)]
    last_action = selected_action.copy() if selected_action else None
        
    return selected_action

def main():
    """Main function"""
    print("\n=== DeepRacer Controller - No Dummy Data ===")
    print("This script gets real-time data from the OptiTrack server")
    print("and sends it to the pFaces server to get control actions.")
    
    print_separator()
    print("INITIALIZATION")
    print(f"OptiTrack server: {LOCALIZATION_SERVER_URL}")
    print(f"pFaces server: {PFACES_SERVER_URL}")
    
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
        try:
            import requests
            response = requests.get(PFACES_SERVER_URL, timeout=2)
            if response.status_code == 200:
                print("✓ Successfully connected to pFaces server")
            else:
                print(f"⚠ pFaces server returned status code: {response.status_code}")
        except Exception as e:
            print(f"✗ Failed to connect to pFaces server: {str(e)}")
            print("\nWARNING: The controller will continue but may fail when calling pFaces.")
    
        print_separator()
        print("GETTING DATA FROM OPTITRACK")
        
        # Get raw data from OptiTrack server
        print("Getting raw data from OptiTrack server...")
        raw_data = localization_server.rest_client.restGETjson()
        
        # Debug: print the raw data received
        print("\nDEBUG: Raw OptiTrack data received:")
        print(raw_data)
        
        # Check for required objects
        required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
        missing_objects = []
        
        for obj in required_objects:
            print(f"DEBUG: Checking for {obj} in data: {'Present' if obj in raw_data else 'Missing'}, "  
                  f"Value: {raw_data.get(obj, 'Not found')}")
            if obj not in raw_data or raw_data.get(obj) == "untracked":
                missing_objects.append(obj)
                print(f"DEBUG: Adding {obj} to missing objects list")
        
        print(f"DEBUG: Missing objects list: {missing_objects}")
        
        if missing_objects:
            raise ValueError(f"Required objects are missing or untracked: {', '.join(missing_objects)}")
        
        # Process DeepRacer1 data
        print("\nProcessing DeepRacer1 data...")
        deepracer_data = raw_data["DeepRacer1"]
        values = deepracer_data.split(',')
        if len(values) >= 5:
            state = [float(values[1].strip()), float(values[2].strip()), 
                     float(values[3].strip()), float(values[4].strip())]
            print(f"DeepRacer state: {state}")
        else:
            raise ValueError(f"Invalid DeepRacer1 data format: {deepracer_data}")
        
        # Process Target4 data
        print("\nProcessing Target4 data...")
        target_hr = calculate_hyperrectangle(raw_data["Target4"], is_target=True)
        if not target_hr:
            raise ValueError(f"Invalid Target4 data format: {raw_data['Target4']}")
        print(f"Target hyperrectangle: {target_hr}")
        
        # Process Obstacle4 data
        print("\nProcessing Obstacle4 data...")
        obstacle_hr = calculate_hyperrectangle(raw_data["Obstacle4"], is_target=False)
        if not obstacle_hr:
            raise ValueError(f"Invalid Obstacle4 data format: {raw_data['Obstacle4']}")
        print(f"Obstacle hyperrectangle: {obstacle_hr}")
        
        # Check if already in target
        target_vals = target_hr.replace('{','').replace('}','').split(',')
        if (state[0] >= float(target_vals[0]) and state[0] <= float(target_vals[1])) and \
           (state[1] >= float(target_vals[2]) and state[1] <= float(target_vals[3])):
            print("\nAlready in the target set. Stopping.")
            return
        
        print("\n--------------------------------------------------\n")
        print("CALLING PFACES SERVER")
        
        # Format the request data clearly
        formatted_state = f"{state[0]:.6f}, {state[1]:.6f}, {state[2]:.6f}, {state[3]:.6f}"
        
        print("\n=== REQUEST DATA ===\n")
        print(f"STATE:\n{formatted_state}")
        print(f"\nTARGET:\n{target_hr}")
        print(f"\nOBSTACLES:\n{obstacle_hr}")
        print("\n=== END REQUEST DATA ===\n")
        
        print("1. Requesting synthesis...")
        print("DEBUG: Full pFaces server URL:", PFACES_SERVER_URL)
        try:
            symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)
            print("DEBUG: Connection established successfully")
            synthesis_response = symbolic_controller.synthesize_controller(obstacle_hr, target_hr, is_last_req=True)
        except Exception as e:
            print("DEBUG: Synthesis request exception:", str(e))
            traceback.print_exc()
        print(f"   Synthesis response: {synthesis_response}")
        
        print("2. Waiting briefly for synthesis...")
        time.sleep(1)
        
        print("3. Creating new connection for control request...")
        try:
            symbolic_controller = RemoteSymbolicController(PFACES_SERVER_URL)  # Create a new connection
            print("DEBUG: Second connection established successfully")
            print("4. Requesting control for state: {0}".format(formatted_state))
            print("DEBUG: Sending exact control request:", formatted_state)
            actions = symbolic_controller.get_controls(formatted_state, is_last_request=True)
            print("DEBUG: Raw response type:", type(actions), "length:", len(str(actions)) if actions else 0)
        except Exception as e:
            print("DEBUG: Control request exception:", str(e))
            traceback.print_exc()
        print(f"4. Received response: {actions}")
        
        # Validate and process the response
        if not actions or actions.strip() == "":
            raise ValueError("Empty response from pFaces server")
        
        # Clean up the response and split it into actions
        actions = actions.replace(" ", "")
        actions_list = actions.split('|')
        
        print(f"5. Split response into {len(actions_list)} potential actions")
        
        # Get the next action - pass the state to maintain direction consistency
        action = get_next_action(actions_list, formatted_state, logger)
        
        print_separator()
        print("FINAL RESULT")
        print(f"Selected action: {action}")
            
    except ValueError as e:
        print_separator()
        print(f"ERROR: {str(e)}")
        print("The controller cannot proceed without valid data.")
        print("Please ensure that:")
        print(f"1. The OptiTrack server is running and accessible")
        print(f"2. The required objects (DeepRacer1, Obstacle4, Target4) are being tracked")
        print(f"3. The pFaces server is running and responding correctly")
        
    except Exception as e:
        print_separator()
        print(f"UNEXPECTED ERROR: {str(e)}")
        if args.debug:
            traceback.print_exc()

if __name__ == "__main__":
    main()
