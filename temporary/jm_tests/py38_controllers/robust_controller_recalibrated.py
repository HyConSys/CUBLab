#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import argparse
import traceback
import math
import socket
import requests

# Simple path setup - assumes running from deepracer-utils/examples/sym_control
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
examples_path = os.path.join(project_root, 'examples')
py38_path = os.path.join(project_root, 'py38_controllers')

# Add all relevant paths to Python's module search path
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files
sys.path.insert(0, examples_path) # Examples
sys.path.insert(0, py38_path)     # Python 3.8 controllers

# Import required modules
from LocalizationServerInterface import LocalizationServerInterface
from RESTApiClient import RESTApiClient

# Constants
THETA_MAX = 1.7  # Maximum theta value (normalized)
RECALIBRATION_MAX = 3.2  # Maximum theta value before recalibration

# Server URLs
LOCALIZATION_SERVER_URL = "http://192.168.1.101:8080"
PFACES_SERVER_URL = "http://192.168.1.100:8080"

# Hardcoded values for fallback
HARDCODED_OBSTACLE = "{0.0,1.0},{0.0,1.0},{-3.2,3.2},{-2.1,2.1}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
HARDCODED_TARGET = "{4.0,5.0},{4.0,5.0},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
HARDCODED_STATE = "1.0,1.0,0.0,0.5"

# Track the last action to maintain driving direction consistency
last_action = None

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
    return f"{x_coords},{{{y_coords},{{{theta_range},{{{velocity_range}|{fixed_part}"

def recalibrate_theta(theta):
    """Recalibrate theta to map the range [-RECALIBRATION_MAX, RECALIBRATION_MAX] to [-THETA_MAX, THETA_MAX]"""
    # Convert to float if it's a string
    if isinstance(theta, str):
        theta = float(theta)
        
    # Calculate the recalibration factor
    recalibration_factor = THETA_MAX / RECALIBRATION_MAX
    
    # Apply the recalibration
    recalibrated_theta = theta * recalibration_factor
    
    # Ensure the result is within bounds
    if recalibrated_theta > THETA_MAX:
        recalibrated_theta = THETA_MAX
    elif recalibrated_theta < -THETA_MAX:
        recalibrated_theta = -THETA_MAX
        
    return recalibrated_theta

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
            print(f"Warning: Invalid state format: {state}")
            return None
            
        x = float(state_parts[0])
        y = float(state_parts[1])
        theta = float(state_parts[2])
        v = float(state_parts[3])
        
        # Recalibrate theta instead of just normalizing it
        theta = recalibrate_theta(theta)
        
        # Reconstruct state with recalibrated theta
        recalibrated_state = f"{x},{y},{theta},{v}"
        
    except Exception as e:
        print(f"Error parsing state: {str(e)}")
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
                logger.error(f"Error parsing action: {str(e)}")
            continue
    
    # Update last action
    last_action = selected_action
    
    return selected_action

def check_pfaces_server(url):
    """Check if the pFaces server is running and accessible"""
    try:
        # Use requests instead of httplib2
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✓ Successfully connected to pFaces server")
            return True
        else:
            print(f"⚠ pFaces server returned status code: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("✗ Connection to pFaces server timed out")
        print("\nWARNING: The controller will continue but may fail when calling pFaces.")
        return False
    except Exception as e:
        print(f"✗ Failed to connect to pFaces server: {str(e)}")
        print("\nWARNING: The controller will continue but may fail when calling pFaces.")
        return False

def main():
    """Main function"""
    print("\n=== DeepRacer Controller - Recalibrated Python 3.8 Version ===")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='DeepRacer Controller - Recalibrated')
    parser.add_argument('--hardcoded', action='store_true', help='Use hardcoded values instead of OptiTrack')
    parser.add_argument('--pfaces-url', type=str, default=PFACES_SERVER_URL, help='pFaces server URL')
    parser.add_argument('--optitrack-url', type=str, default=LOCALIZATION_SERVER_URL, help='OptiTrack server URL')
    args = parser.parse_args()
    
    # Update URLs if provided
    pfaces_url = args.pfaces_url
    optitrack_url = args.optitrack_url
    
    print(f"pFaces server URL: {pfaces_url}")
    print(f"OptiTrack server URL: {optitrack_url}")
    print(f"Using theta recalibration: [-{RECALIBRATION_MAX}, {RECALIBRATION_MAX}] → [-{THETA_MAX}, {THETA_MAX}]")
    
    # Check if the pFaces server is running
    check_pfaces_server(pfaces_url)
    
    # Import RemoteSymbolicController here to avoid circular imports
    try:
        from RemoteSymbolicController import RemoteSymbolicController
    except ImportError:
        print("Error: Could not import RemoteSymbolicController. Make sure it's in the Python path.")
        return
    
    # Main control loop
    try:
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
                    # Use a shorter timeout for OptiTrack to avoid long waits
                    # Create a custom RESTApiClient with a short timeout
                    rest_client = RESTApiClient(optitrack_url, timeout=1)
                    
                    print("Using shortened timeout (1 second) for faster response")
                    raw_data = rest_client.restGETjson()
                    
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
                            print(f"Error: Required object '{obj}' not found in OptiTrack data")
                            print("Using hardcoded values instead")
                            obstacles_str = HARDCODED_OBSTACLE
                            target_str = HARDCODED_TARGET
                            state_str = HARDCODED_STATE
                            raise Exception(f"Required object '{obj}' not found")
                    
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
                    
                    # Recalibrate theta instead of just normalizing it
                    theta = recalibrate_theta(theta)
                    
                    # Create state string
                    state_str = f"{x},{y},{theta},{v}"
                    print(f"DeepRacer state: {state_str} (theta recalibrated from {values[3].strip()})")
                    
                    # Create hyperrectangle strings
                    localization_server = LocalizationServerInterface(optitrack_url)
                    
                    # Get target hyperrectangle
                    target_data = localization_server.get_hyper_rec_str("Target")
                    if not target_data:
                        print("Error: No target data found")
                        print("Using hardcoded target")
                        target_str = HARDCODED_TARGET
                    else:
                        target_name, target_rect = target_data[0]
                        target_str = create_fixed_hyperrectangle(target_rect, is_target=True)
                        print(f"Target hyperrectangle: {target_str}")
                    
                    # Get obstacle hyperrectangle
                    obstacle_data = localization_server.get_hyper_rec_str("Obstacle")
                    if not obstacle_data:
                        print("Error: No obstacle data found")
                        print("Using hardcoded obstacle")
                        obstacles_str = HARDCODED_OBSTACLE
                    else:
                        obstacle_name, obstacle_rect = obstacle_data[0]
                        obstacles_str = create_fixed_hyperrectangle(obstacle_rect, is_target=False)
                        print(f"Obstacle hyperrectangle: {obstacles_str}")
                    
                except Exception as e:
                    if "Fast fallback" not in str(e):
                        print(f"Error getting OptiTrack data: {str(e)}")
                        print("Using hardcoded values instead")
                    obstacles_str = HARDCODED_OBSTACLE
                    target_str = HARDCODED_TARGET
                    state_str = HARDCODED_STATE
            
            # Create a new RemoteSymbolicController for synthesis
            print("\nCreating RemoteSymbolicController for synthesis...")
            controller = RemoteSymbolicController(pfaces_url)
            
            # Synthesize controller
            print("Synthesizing controller...")
            controller.synthesize_controller(obstacles_str, target_str)
            
            # Wait for synthesis to complete
            print("Waiting for synthesis to complete...")
            time.sleep(1)
            
            # Create a new RemoteSymbolicController for getting controls
            # This is critical - must follow the exact pattern of synth_and_get.py
            print("Creating new RemoteSymbolicController for getting controls...")
            controller = RemoteSymbolicController(pfaces_url)
            
            # Get controls
            print(f"Getting controls for state: {state_str}")
            actions = controller.get_controls(state_str)
            
            if not actions:
                print("Error: No actions returned from controller")
                time.sleep(1)
                continue
            
            # Get next action
            action = get_next_action(actions, state_str)
            
            if action:
                print(f"Selected action: {action}")
            else:
                print("Error: Could not select an action")
            
            # Sleep for a bit
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nController stopped by user")
    except Exception as e:
        print(f"\nError in main loop: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
