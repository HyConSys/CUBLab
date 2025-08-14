#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import math
import gc
import json
import traceback
import httplib2
import sys
import os
from signal import signal, SIGINT
from sys import exit

# Insert project paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
src_path = os.path.join(project_root, 'src')
examples_path = os.path.join(project_root, 'examples')
sym_control_path = os.path.join(project_root, 'examples/sym_control')

# Add all relevant paths to Python's module search path
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files
sys.path.insert(0, examples_path) # Examples
sys.path.insert(0, sym_control_path) # Symbolic controller

# Import DeepRacer modules
import DeepRacer
from RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger

# Configuration
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
LOCALIZATION_SERVER_URL = "http://" + LOCALIZATION_SERVER_IPPORT + "/OptiTrackRestServer"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/" + ROBOT_NAME

# Theta range limits based on testing
THETA_MIN = -1.7  # Determined through testing
THETA_MAX = 1.7   # Determined through precise testing (values > 1.7 fail)

# Control loop parameters
CONTROL_LOOP_INTERVAL = 0.1  # seconds
MAX_RUNTIME = 300  # seconds (5 minutes)

# Initialize logger
logger = Logger()

# Initialize variables
curr_target = 0
last_action = None
running = True

def normalize_theta(theta):
    """Normalize theta to be within the acceptable range"""
    # First, normalize to [-pi, pi]
    normalized = ((theta + math.pi) % (2 * math.pi)) - math.pi
    
    # Then, clamp to the acceptable range
    if normalized > THETA_MAX:
        print("WARNING: Theta value {0} is too large, clamping to {1}".format(normalized, THETA_MAX))
        return THETA_MAX
    elif normalized < THETA_MIN:
        print("WARNING: Theta value {0} is too small, clamping to {1}".format(normalized, THETA_MIN))
        return THETA_MIN
    
    return normalized

def get_optitrack_data():
    """Get data from OptiTrack server with fresh connection for each request"""
    try:
        # Create a new HTTP connection for each request
        http = httplib2.Http(timeout=180)
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        
        if response.status != 200:
            print("HTTP Error: Status {0}".format(response.status))
            return None
            
        # Parse JSON response
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return json.loads(content)
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

def create_hyperrectangle(data, is_target=False):
    """Create a hyperrectangle from object data"""
    try:
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
            
            # Create hyperrectangle
            if is_target:
                return "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}".format(
                    x_min, x_max, y_min, y_max)
            else:  # Obstacle
                return "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}".format(
                    x_min, x_max, y_min, y_max)
        else:
            return None
    except Exception as e:
        print("Error creating hyperrectangle: {0}".format(str(e)))
        return None

def get_next_action(last_action, new_actions, state, logger):
    """Select the best action from the available actions"""
    try:
        # Convert state string to list of floats if it's a string
        if isinstance(state, str):
            state = list(map(float, state.replace("(","").replace(")","").split(',')))
        
        new_actions_conc = []
        good_candidate_idx = 0
        idx = 0
        
        for action_str in new_actions:
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
            
            # Convert to DeepRacer format
            try:
                new_action = [DeepRacer.unmap_angle(float(new_action[0])), 
                             DeepRacer.unmap_trottle(float(new_action[1]))]
                new_actions_conc.append(new_action)
                
                # Selection criterion: first action with same direction as last action
                if last_action is not None:
                    if (last_action[1] > 0 and new_action[1] > 0) or (last_action[1] < 0 and new_action[1] < 0):
                        good_candidate_idx = idx
                        break
            except ValueError:
                logger.log("Could not convert action to float: {0}".format(action_str))
            
            idx += 1
        
        # Check if we have any valid actions
        if not new_actions_conc:
            logger.log("No valid actions found")
            return None
        
        # Store the selected action for next time
        selected_action = new_actions_conc[min(good_candidate_idx, len(new_actions_conc)-1)]
        return selected_action
        
    except Exception as e:
        logger.log("Error in get_next_action: {0}".format(str(e)))
        return None

def control_loop():
    """Main control loop that directly manages HTTP connections"""
    global curr_target
    global last_action
    global running
    
    print("\n=== Starting Direct Control Loop (Python 2.7) ===")
    print("OptiTrack server: {0}".format(LOCALIZATION_SERVER_URL))
    print("pFaces server: {0}".format(SYMCONTROL_SERVER_URI))
    print("Control loop interval: {0}s".format(CONTROL_LOOP_INTERVAL))
    print("Max runtime: {0}s ({1} minutes)".format(MAX_RUNTIME, MAX_RUNTIME/60))
    print("Theta range: [{0}, {1}]".format(THETA_MIN, THETA_MAX))
    
    start_time = time.time()
    targets = []
    
    while running and (time.time() - start_time) < MAX_RUNTIME:
        loop_start = time.time()
        
        try:
            # Get data from OptiTrack
            print("\n--- New Control Cycle ---")
            print("Getting data from OptiTrack...")
            raw_data = get_optitrack_data()
            
            if not raw_data:
                print("No data from OptiTrack, skipping cycle")
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Check for required objects
            required_objects = ["DeepRacer1", "Target4", "Obstacle4"]
            missing_objects = []
            
            for obj in required_objects:
                if obj not in raw_data or raw_data[obj] == "untracked":
                    missing_objects.append(obj)
            
            if missing_objects:
                print("Missing required objects: {0}".format(", ".join(missing_objects)))
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Process DeepRacer state
            deepracer_data = raw_data["DeepRacer1"]
            values = deepracer_data.split(',')
            
            if len(values) >= 5:
                x = float(values[1].strip())
                y = float(values[2].strip())
                z = float(values[3].strip())
                theta = float(values[4].strip())
                
                # Normalize theta
                normalized_theta = normalize_theta(theta)
                
                # Create state
                state = [x, y, z, normalized_theta]
                state_str = "{0:.6f}, {1:.6f}, {2:.6f}, {3:.6f}".format(x, y, z, normalized_theta)
                print("DeepRacer state: {0}".format(state_str))
                
                if abs(normalized_theta - theta) > 0.001:
                    print("Original theta: {0:.6f}, Normalized to: {1:.6f}".format(theta, normalized_theta))
            else:
                print("Invalid DeepRacer data format")
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Process targets
            if not targets:
                # Find all targets
                for key in raw_data:
                    if "Target" in key and raw_data[key] != "untracked":
                        target_hr = create_hyperrectangle(raw_data[key], is_target=True)
                        if target_hr:
                            targets.append((key, target_hr))
                
                if not targets:
                    print("No valid targets found")
                    time.sleep(CONTROL_LOOP_INTERVAL)
                    continue
                    
                print("Found {0} targets".format(len(targets)))
            
            # Check if curr_target is valid
            if curr_target >= len(targets):
                curr_target = 0
                
            # Get current target
            target_name, target_str = targets[curr_target]
            print("Using target #{0}: {1}".format(curr_target, target_name))
            
            # Check if already in target
            target_vals = target_str.replace('{','').replace('}','').split(',')
            if (state[0] >= float(target_vals[0]) and state[0] <= float(target_vals[1])) and \
               (state[1] >= float(target_vals[2]) and state[1] <= float(target_vals[3])):
                print("Already in target {0}, moving to next target".format(target_name))
                curr_target += 1
                if curr_target >= len(targets):
                    curr_target = 0
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Process obstacles
            obstacles = []
            for key in raw_data:
                if "Obstacle" in key and raw_data[key] != "untracked":
                    obstacle_hr = create_hyperrectangle(raw_data[key], is_target=False)
                    if obstacle_hr:
                        obstacles.append((key, obstacle_hr))
            
            if not obstacles:
                print("No valid obstacles found")
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            print("Found {0} obstacles".format(len(obstacles)))
            
            # Create obstacle string
            obstacle_str = obstacles[0][1]  # Use first obstacle
            
            # Create a new symbolic controller for each request
            print("Creating new symbolic controller...")
            sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
            
            # Request synthesis
            print("Requesting synthesis...")
            sym_control.synthesize_controller(obstacle_str, target_str, is_last_req=True)
            
            # Wait briefly for synthesis
            print("Waiting for synthesis...")
            time.sleep(5)
            
            # Create a new controller for control request
            print("Creating new controller for control request...")
            sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
            
            # Format state string
            s_send = "({0})".format(state_str)
            print("Requesting control for state: {0}".format(s_send))
            
            # Get controls
            action_str = sym_control.get_controls(s_send, is_last_request=True)
            print("Received actions: {0}".format(action_str))
            
            # Check for empty response
            if not action_str or action_str.strip() == "":
                print("Empty response from controller")
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Parse actions
            actions_list = action_str.replace(" ", "").split('|')
            
            # Get next action
            action = get_next_action(last_action, actions_list, state, logger)
            
            if not action:
                print("Could not get a valid action")
                time.sleep(CONTROL_LOOP_INTERVAL)
                continue
                
            # Save last action
            last_action = action
            
            # Print selected action
            print("Selected action: steering = {0}, speed = {1}".format(action[0], action[1]))
            
            # Here you would send the action to the DeepRacer
            # For now, we'll just print it
            
        except Exception as e:
            print("Error in control loop: {0}".format(str(e)))
            traceback.print_exc()
        
        # Calculate sleep time to maintain loop interval
        elapsed = time.time() - loop_start
        sleep_time = max(0, CONTROL_LOOP_INTERVAL - elapsed)
        
        if sleep_time > 0:
            print("Cycle completed in {0:.2f}s, sleeping for {1:.2f}s".format(elapsed, sleep_time))
            time.sleep(sleep_time)
        else:
            print("Cycle took {0:.2f}s (longer than interval)".format(elapsed))
        
        # Force garbage collection at the end of each cycle
        gc.collect()
    
    print("Control loop finished after {0:.2f}s".format(time.time() - start_time))

def sig_handler(signal_received, frame):
    """Handle SIGINT (Ctrl+C)"""
    global running
    print("Exiting gracefully...")
    running = False

if __name__ == "__main__":
    # Set up signal handler
    signal(SIGINT, sig_handler)
    
    try:
        # Run the control loop
        control_loop()
    except Exception as e:
        print("Unhandled exception: {0}".format(str(e)))
        traceback.print_exc()
    finally:
        # Force final garbage collection
        gc.collect()
