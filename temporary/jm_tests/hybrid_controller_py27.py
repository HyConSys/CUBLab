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
import gc

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

# Import required modules
import httplib2
from LocalizationServerInterface import LocalizationServerInterface
from RemoteSymbolicController import RemoteSymbolicController

# Constants
THETA_MAX = 1.7  # Maximum theta value (normalized)

# Server URLs
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"
PFACES_SERVER_URL = "http://192.168.1.100:8080"

# Hardcoded values for fallback
HARDCODED_OBSTACLE = "{0.0,1.0},{0.0,1.0},{-3.2,3.2},{-2.1,2.1}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
HARDCODED_TARGET = "{4.0,5.0},{4.0,5.0},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
HARDCODED_STATE = "1.0,1.0,0.0,0.5"

# Track the last action to maintain driving direction consistency
last_action = None

# Cache for OptiTrack data
optitrack_cache = None
last_optitrack_time = 0
CACHE_VALIDITY_PERIOD = 5  # seconds

def print_separator():
    """Print a separator line for better readability"""
    print("\n" + "-" * 80)

def create_fixed_hyperrectangle(data, is_target=False):
    """Create a fixed hyperrectangle that uses real coordinates but follows the hardcoded format
    
    This follows the specific format required by the pFaces server:
    - First part uses real coordinates from OptiTrack
    - Second part (after | separator) uses hardcoded coordinates: {2.0,3.0},{2.0,3.0}
    - Theta and velocity ranges are the same in both parts
    """
    # Extract the coordinates from the data
    parts = data.split('},{')
    if len(parts) < 4:
        raise ValueError("Invalid data format")
    
    # First two parts are x and y coordinates
    x_coords = parts[0]
    y_coords = parts[1]
    
    # Last two parts are theta and velocity ranges
    theta_range = parts[2]
    velocity_range = parts[3]
    
    # Create the fixed hyperrectangle string
    if is_target:
        # For targets
        fixed_part = "{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
    else:
        # For obstacles
        fixed_part = "{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
    
    # Combine real coordinates with fixed format
    return "{0},{{{1}}},{{{2}}},{{{3}|{4}".format(x_coords, y_coords, theta_range, velocity_range, fixed_part)

def normalize_theta(theta):
    """Normalize theta to the range [-THETA_MAX, THETA_MAX]"""
    # Convert to float if it's a string
    if isinstance(theta, str):
        theta = float(theta)
        
    # Clamp theta to the range [-THETA_MAX, THETA_MAX]
    if theta > THETA_MAX:
        theta = THETA_MAX
    elif theta < -THETA_MAX:
        theta = -THETA_MAX
        
    return theta

def get_optitrack_data(first_connection=False):
    """Get data from OptiTrack server with appropriate timeout
    
    If first_connection is True, use a longer timeout to ensure initial connection.
    Otherwise, use a shorter timeout for subsequent requests.
    """
    global optitrack_cache, last_optitrack_time
    
    # Check if we can use cached data
    current_time = time.time()
    if not first_connection and optitrack_cache is not None:
        if current_time - last_optitrack_time < CACHE_VALIDITY_PERIOD:
            print("Using cached OptiTrack data ({:.1f} seconds old)".format(current_time - last_optitrack_time))
            return optitrack_cache
    
    # Determine timeout based on whether this is the first connection
    timeout = 180 if first_connection else 3  # 3 minutes for first connection, 3 seconds for subsequent
    
    try:
        # Create a new HTTP connection for each request
        print("Connecting to OptiTrack with {} second timeout...".format(timeout))
        start_time = time.time()
        http = httplib2.Http(timeout=timeout)
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        elapsed = time.time() - start_time
        print("OptiTrack connection established in {:.2f} seconds".format(elapsed))
        
        if response.status != 200:
            print("HTTP Error: Status {0}".format(response.status))
            return None
            
        # Parse JSON response
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        data = json.loads(content)
        
        # Update cache
        optitrack_cache = data
        last_optitrack_time = current_time
        
        return data
    except socket.timeout:
        print("Connection to OptiTrack timed out after {} seconds".format(timeout))
        return None
    except Exception as e:
        print("Error getting OptiTrack data: {0}".format(str(e)))
        return None
    finally:
        # Clean up HTTP connection
        try:
            http.clear()
        except:
            pass
        # Force garbage collection
        gc.collect()

def get_next_action(actions_list, state, logger=None):
    """Function to get next action from the list of actions, using DeepRacer-Utils approach"""
    global last_action
    
    if not actions_list:
        print("Warning: Empty actions list")
        return None
    
    # Parse state
    try:
        state_parts = state.split(',')
        if len(state_parts) < 4:
            print("Warning: Invalid state format: {0}".format(state))
            return None
            
        x = float(state_parts[0])
        y = float(state_parts[1])
        theta = float(state_parts[2])
        v = float(state_parts[3])
        
        # Normalize theta to the range [-THETA_MAX, THETA_MAX]
        theta = normalize_theta(theta)
        
        # Reconstruct state with normalized theta
        normalized_state = "{0},{1},{2},{3}".format(x, y, theta, v)
        
    except Exception as e:
        print("Error parsing state: {0}".format(str(e)))
        return None
    
    # Find the best action
    min_distance = float('inf')
    selected_action = None
    
    for action in actions_list:
        # Parse action
        try:
            action_parts = action.split(',')
            if len(action_parts) < 5:
                continue
                
            action_x = float(action_parts[0])
            action_y = float(action_parts[1])
            action_theta = float(action_parts[2])
            action_v = float(action_parts[3])
            action_u = action_parts[4]  # Control input
            
            # Calculate distance in state space
            dx = x - action_x
            dy = y - action_y
            dtheta = theta - action_theta
            dv = v - action_v
            
            # Weight the distance components
            distance = math.sqrt(dx*dx + dy*dy + 0.5*dtheta*dtheta + 0.1*dv*dv)
            
            # Prefer actions that maintain the same direction as the last action
            if last_action is not None and last_action == action_u:
                distance *= 0.9  # Reduce distance by 10% to favor the same action
            
            if distance < min_distance:
                min_distance = distance
                selected_action = action_u
                
        except Exception as e:
            if logger:
                logger.error("Error parsing action: {0}".format(str(e)))
            continue
    
    # Update last action
    last_action = selected_action
    
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
    print("\n=== DeepRacer Hybrid Controller (Python 2.7) ===")
    print("This controller uses a long timeout for the initial connection")
    print("and caches data for subsequent requests")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='DeepRacer Hybrid Controller')
    parser.add_argument('--hardcoded', action='store_true', help='Use hardcoded values instead of OptiTrack')
    parser.add_argument('--pfaces-url', type=str, default=PFACES_SERVER_URL, help='pFaces server URL')
    parser.add_argument('--optitrack-url', type=str, default=LOCALIZATION_SERVER_URL, help='OptiTrack server URL')
    parser.add_argument('--cache-time', type=int, default=CACHE_VALIDITY_PERIOD, help='Cache validity period in seconds')
    args = parser.parse_args()
    
    # Update URLs if provided
    global LOCALIZATION_SERVER_URL, PFACES_SERVER_URL, CACHE_VALIDITY_PERIOD
    PFACES_SERVER_URL = args.pfaces_url
    LOCALIZATION_SERVER_URL = args.optitrack_url
    CACHE_VALIDITY_PERIOD = args.cache_time
    
    print("pFaces server URL: {0}".format(PFACES_SERVER_URL))
    print("OptiTrack server URL: {0}".format(LOCALIZATION_SERVER_URL))
    print("Cache validity period: {0} seconds".format(CACHE_VALIDITY_PERIOD))
    
    # Check if the pFaces server is running
    check_pfaces_server(PFACES_SERVER_URL)
    
    # Main control loop
    try:
        # First, try to establish initial connection to OptiTrack with longer timeout
        if not args.hardcoded:
            print("\nEstablishing initial connection to OptiTrack...")
            initial_data = get_optitrack_data(first_connection=True)
            if initial_data:
                print("✓ Successfully established initial connection to OptiTrack")
            else:
                print("⚠ Could not establish initial connection to OptiTrack")
                print("Will use hardcoded values for first iteration")
        
        while True:
            print_separator()
            
            # Get hyperrectangle strings
            if args.hardcoded:
                print("Using hardcoded values...")
                obstacles_str = HARDCODED_OBSTACLE
                target_str = HARDCODED_TARGET
                state_str = HARDCODED_STATE
            else:
                print("\nGetting real-time data from OptiTrack...")
                try:
                    # Get data from OptiTrack (using cache if available)
                    raw_data = get_optitrack_data(first_connection=False)
                    
                    if not raw_data:
                        print("Error: OptiTrack server returned empty data")
                        print("Using hardcoded values instead")
                        obstacles_str = HARDCODED_OBSTACLE
                        target_str = HARDCODED_TARGET
                        state_str = HARDCODED_STATE
                        raise Exception("Fast fallback to hardcoded values")
                        
                    # Check for required objects
                    required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
                    for obj in required_objects:
                        if obj not in raw_data:
                            print("Error: Required object '{0}' not found in OptiTrack data".format(obj))
                            print("Using hardcoded values instead")
                            obstacles_str = HARDCODED_OBSTACLE
                            target_str = HARDCODED_TARGET
                            state_str = HARDCODED_STATE
                            raise Exception("Required object '{0}' not found".format(obj))
                    
                    # Get DeepRacer state
                    deepracer_data = raw_data["DeepRacer1"]
                    if deepracer_data == "untracked":
                        print("Error: DeepRacer is untracked")
                        print("Using hardcoded values instead")
                        obstacles_str = HARDCODED_OBSTACLE
                        target_str = HARDCODED_TARGET
                        state_str = HARDCODED_STATE
                        raise Exception("DeepRacer is untracked")
                    
                    # Parse DeepRacer state
                    values = deepracer_data.split(',')
                    x = float(values[1].strip())
                    y = float(values[2].strip())
                    theta = float(values[3].strip())
                    v = 0.5  # Fixed velocity
                    
                    # Normalize theta
                    theta = normalize_theta(theta)
                    
                    # Create state string
                    state_str = "{0},{1},{2},{3}".format(x, y, theta, v)
                    print("DeepRacer state: {0}".format(state_str))
                    
                    # Create hyperrectangle strings
                    localization_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
                    
                    # Get target hyperrectangle
                    target_data = localization_server.get_hyper_rec_str("Target")
                    if not target_data:
                        print("Error: No target data found")
                        print("Using hardcoded target")
                        target_str = HARDCODED_TARGET
                    else:
                        target_name, target_rect = target_data[0]
                        target_str = create_fixed_hyperrectangle(target_rect, is_target=True)
                        print("Target hyperrectangle: {0}".format(target_str))
                    
                    # Get obstacle hyperrectangle
                    obstacle_data = localization_server.get_hyper_rec_str("Obstacle")
                    if not obstacle_data:
                        print("Error: No obstacle data found")
                        print("Using hardcoded obstacle")
                        obstacles_str = HARDCODED_OBSTACLE
                    else:
                        obstacle_name, obstacle_rect = obstacle_data[0]
                        obstacles_str = create_fixed_hyperrectangle(obstacle_rect, is_target=False)
                        print("Obstacle hyperrectangle: {0}".format(obstacles_str))
                    
                except Exception as e:
                    if "Fast fallback" not in str(e):
                        print("Error getting OptiTrack data: {0}".format(str(e)))
                        print("Using hardcoded values instead")
                    obstacles_str = HARDCODED_OBSTACLE
                    target_str = HARDCODED_TARGET
                    state_str = HARDCODED_STATE
            
            # Create a new RemoteSymbolicController for synthesis
            print("\nCreating RemoteSymbolicController for synthesis...")
            controller = RemoteSymbolicController(PFACES_SERVER_URL)
            
            # Synthesize controller
            print("Synthesizing controller...")
            controller.synthesize_controller(obstacles_str, target_str)
            
            # Wait for synthesis to complete
            print("Waiting for synthesis to complete...")
            time.sleep(1)
            
            # Create a new RemoteSymbolicController for getting controls
            # This is critical - must follow the exact pattern of synth_and_get.py
            print("Creating new RemoteSymbolicController for getting controls...")
            controller = RemoteSymbolicController(PFACES_SERVER_URL)
            
            # Get controls
            print("Getting controls for state: {0}".format(state_str))
            actions = controller.get_controls(state_str)
            
            if not actions:
                print("Error: No actions returned from controller")
                time.sleep(1)
                continue
            
            # Get next action
            action = get_next_action(actions, state_str)
            
            if action:
                print("Selected action: {0}".format(action))
            else:
                print("Error: Could not select an action")
            
            # Sleep for a bit
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nController stopped by user")
    except Exception as e:
        print("\nError in main loop: {0}".format(str(e)))
        traceback.print_exc()

if __name__ == "__main__":
    main()
