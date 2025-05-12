#!/usr/bin/env python3
import sys
import os
import time
import requests
import argparse
import traceback
import math

# Get path to project root (deepracer-utils-github)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)  # so 'examples' is found
sys.path.insert(0, os.path.join(project_root, 'src'))  # so 'RESTApiClient' is found

from examples.sym_control.RemoteSymbolicController import RemoteSymbolicController

# Parse command line arguments
parser = argparse.ArgumentParser(description='DeepRacer Controller - Robust Version')
parser.add_argument('--optitrack-server', default='192.168.1.194:12345', help='OptiTrack server IP:port')
parser.add_argument('--pfaces-server', default='192.168.1.144:12345', help='pFaces server IP:port')
parser.add_argument('--use-hardcoded', action='store_true', help='Use hardcoded values instead of real data')
parser.add_argument('--debug', action='store_true', help='Print debug information')
args = parser.parse_args()

# Configuration
OPTITRACK_URL = f"http://{args.optitrack_server}/OptiTrackRestServer"
PFACES_URL = f"http://{args.pfaces_server}/pFaces/REST/dictionary/DeepRacer1"

# Hardcoded values from the working example
HARDCODED_OBSTACLE = "{0.5,1.5},{0.5,1.5},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{-2.1,2.1}"
HARDCODED_TARGET = "{0.5,1.5},{0.5,1.5},{-3.2,3.2},{0.0,0.8}|{2.0,3.0},{2.0,3.0},{-3.2,3.2},{0.0,0.8}"
HARDCODED_STATE = "0.0, 0.0, 0.0, 0.0"

# Theta range limits based on testing
THETA_MIN = -1.7  # Assumed symmetric with positive limit
THETA_MAX = 1.7   # Determined through precise testing (values > 1.7 fail)

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
            return f"{{{x_min:.4f},{x_max:.4f}}},{{{y_min:.4f},{y_max:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}|{{2.0,3.0}},{{2.0,3.0}},{{-3.2,3.2}},{{0.0,0.8}}"
        else:  # Obstacle
            return f"{{{x_min:.4f},{x_max:.4f}}},{{{y_min:.4f},{y_max:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}|{{2.0,3.0}},{{2.0,3.0}},{{-3.2,3.2}},{{-2.1,2.1}}"
    else:
        return None

def normalize_theta(theta):
    """Normalize theta to be within the acceptable range"""
    # First, normalize to [-pi, pi]
    normalized = ((theta + math.pi) % (2 * math.pi)) - math.pi
    
    # Then, clamp to the acceptable range
    if normalized > THETA_MAX:
        print(f"WARNING: Theta value {normalized} is too large, clamping to {THETA_MAX}")
        return THETA_MAX
    elif normalized < THETA_MIN:
        print(f"WARNING: Theta value {normalized} is too small, clamping to {THETA_MIN}")
        return THETA_MIN
    
    return normalized

def check_pfaces_server():
    """Check if the pFaces server is running and accessible"""
    try:
        response = requests.get(PFACES_URL, timeout=2)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False

def main():
    """Main function"""
    print("\n=== DeepRacer Controller - Robust Version ===")
    print("This controller handles theta range limits and connection issues")
    
    print_separator()
    print("CONFIGURATION")
    print(f"OptiTrack server: {OPTITRACK_URL}")
    print(f"pFaces server: {PFACES_URL}")
    print(f"Theta range: [{THETA_MIN}, {THETA_MAX}]")
    print(f"Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    
    # Check if pFaces server is running
    if not check_pfaces_server():
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
            print(f"Obstacles: {obstacles_str}")
            print(f"Target: {target_str}")
            print(f"State: {state_str}")
        else:
            print("\nGetting real-time data from OptiTrack...")
            try:
                response = requests.get(OPTITRACK_URL, timeout=2)
                if response.status_code != 200:
                    print(f"Error: OptiTrack server returned status {response.status_code}")
                    return
                    
                raw_data = response.json()
                
                # Check for required objects
                required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
                missing_objects = []
                
                for obj in required_objects:
                    if obj not in raw_data or raw_data[obj] == "untracked":
                        missing_objects.append(obj)
                
                if missing_objects:
                    print(f"Error: Required objects missing: {', '.join(missing_objects)}")
                    return
                
                # Process DeepRacer1 data
                deepracer_data = raw_data["DeepRacer1"]
                values = deepracer_data.split(',')
                if len(values) >= 5:
                    x = float(values[1].strip())
                    y = float(values[2].strip())
                    z = float(values[3].strip())
                    theta = float(values[4].strip())
                    
                    # Normalize theta to be within the acceptable range
                    normalized_theta = normalize_theta(theta)
                    
                    state_str = f"{x:.6f}, {y:.6f}, {z:.6f}, {normalized_theta:.6f}"
                    print(f"DeepRacer state: {state_str}")
                    
                    # Check if theta was normalized
                    if abs(normalized_theta - theta) > 0.001:
                        print(f"Original theta: {theta:.6f}, Normalized to: {normalized_theta:.6f}")
                        print("WARNING: The DeepRacer's orientation is outside the optimal range")
                        print("Consider reorienting the DeepRacer to get better control actions")
                else:
                    print(f"Error: Invalid DeepRacer1 data format")
                    return
                
                # Create fixed hyperrectangles
                target_str = create_fixed_hyperrectangle(raw_data["Target4"], is_target=True)
                obstacles_str = create_fixed_hyperrectangle(raw_data["Obstacle4"], is_target=False)
                
                if not target_str or not obstacles_str:
                    print("Error: Could not create hyperrectangles")
                    return
                    
                if args.debug:
                    print(f"Target hyperrectangle: {target_str}")
                    print(f"Obstacle hyperrectangle: {obstacles_str}")
                    
            except Exception as e:
                print(f"Error getting OptiTrack data: {str(e)}")
                print("Using hardcoded values instead")
                obstacles_str = HARDCODED_OBSTACLE
                target_str = HARDCODED_TARGET
                state_str = HARDCODED_STATE
        
        # Now follow the exact pattern of synth_and_get.py
        print("\nCreating symbolic controller...")
        try:
            symbolic_controller = RemoteSymbolicController(PFACES_URL)
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
            symbolic_controller = RemoteSymbolicController(PFACES_URL)  # Create a new controller
        except Exception as e:
            if "mode" in str(e):
                print_separator()
                print("ERROR: Could not get server mode")
                print("Please restart the pFaces server and try again")
                return
            else:
                raise
        
        print(f"Requesting control for state: {state_str}")
        try:
            action = symbolic_controller.get_controls(state_str, is_last_request=True)
        except KeyError as e:
            if "is_control_ready" in str(e):
                print_separator()
                print("ERROR: Server did not return control ready status")
                print("This can happen when the theta value is outside the acceptable range")
                print(f"Current theta value: {normalized_theta:.6f}")
                print("Please reorient the DeepRacer to have a theta value closer to 0")
                print(f"Acceptable theta range: [{THETA_MIN}, {THETA_MAX}]")
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
        
        print("Received action:", action)
        
        # Check if we got a valid action
        if not action or action.strip() == "":
            print_separator()
            print("ERROR: Received empty action from server")
            print("This can happen when the state is outside the controller's domain")
            print("Please try again with a different state or orientation")
            return
        
        # Parse the action
        actions = action.replace(" ", "").split('|')
        if not actions:
            print("No valid actions found")
            return
            
        # Select the first action for simplicity
        selected_action = actions[0].replace("(", "").replace(")", "").split(',')
        if len(selected_action) != 2:
            print("Invalid action format")
            return
            
        try:
            steering = float(selected_action[0])
            speed = float(selected_action[1])
            
            print_separator()
            print("FINAL RESULT")
            print(f"Selected action: steering = {steering}, speed = {speed}")
        except ValueError:
            print("Could not parse action values")
            
    except Exception as e:
        print_separator()
        print(f"UNEXPECTED ERROR: {str(e)}")
        if args.debug:
            traceback.print_exc()

if __name__ == "__main__":
    main()
