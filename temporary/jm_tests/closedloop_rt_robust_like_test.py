#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import math
import gc
import json
import traceback
from signal import signal, SIGINT
from sys import exit
from sys import path

# insert src into script path
path.insert(1, '../../src')

import DeepRacer
import httplib2
from DeepRacerController import DeepRacerController
from RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger
from RESTApiClient import RESTApiClient

# Print httplib2 version for debugging
try:
    print("Using httplib2 version: " + httplib2.__version__)
except:
    print("Could not determine httplib2 version")

# Configuration
STOP_AFTER_LAST_TARGET = False
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME

# Theta range limits based on testing
THETA_MIN = -1.7  # Determined through testing
THETA_MAX = 1.7   # Determined through precise testing (values > 1.7 fail)

# Initialize variables
curr_target = 0
target_vals = []
hrListTar = []
tau = 0.0
localization_server = None
sym_control = None
last_action = None

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Create a custom RESTApiClient with better error handling and timeouts
class RobustRESTApiClient(RESTApiClient):
    def __init__(self, url, timeout=10):
        self.url = url
        self.http = httplib2.Http(timeout=timeout)
        print("Created RobustRESTApiClient with URL: " + url)
        
    def restGETjson(self, query=""):
        full_url = self.url + query
        print("Connecting to: " + full_url)
        start_time = time.time()
        
        for attempt in range(MAX_RETRIES):
            try:
                response, content = self.http.request(full_url, method="GET")
                elapsed = time.time() - start_time
                
                if response.status != 200:
                    print("HTTP Error: Status {0} after {1:.2f} seconds (attempt {2}/{3})".format(
                        response.status, elapsed, attempt+1, MAX_RETRIES))
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        raise Exception("HTTP Error: " + str(response.status))
                
                print("Response received in {0:.2f} seconds".format(elapsed))
                
                # Force garbage collection after network operation
                gc.collect()
                
                # Parse JSON with error handling
                try:
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    return json.loads(content)
                except ValueError as e:
                    print("JSON parsing error: " + str(e))
                    print("Response content: " + str(content)[:100] + "...")
                    raise
                    
            except Exception as e:
                elapsed = time.time() - start_time
                print("Error after {0:.2f} seconds (attempt {1}/{2}): {3}".format(
                    elapsed, attempt+1, MAX_RETRIES, str(e)))
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise
        
        raise Exception("Failed after " + str(MAX_RETRIES) + " attempts")
    
    def __del__(self):
        """Explicit cleanup of HTTP resources"""
        if hasattr(self, 'http'):
            try:
                self.http.clear()
            except:
                pass

# Custom LocalizationServerInterface with better error handling
class RobustLocalizationServerInterface:
    def __init__(self, url):
        print("Initializing RobustLocalizationServerInterface with URL: " + url)
        self.rest_client = RobustRESTApiClient(url)
        
    def get_rigid_body_data(self, rbName):
        """Get rigid body data with error handling"""
        try:
            response = self.rest_client.restGETjson("?RigidBody=" + rbName)
            if rbName not in response:
                print("Warning: '" + rbName + "' not found in server response")
                return "untracked"
            return response[rbName]
        except Exception as e:
            print("Error getting rigid body data for '" + rbName + "': " + str(e))
            return "untracked"
            
    def get_hyper_rec_str(self, objType):
        """Get hyperrectangle string with error handling"""
        try:
            response = self.rest_client.restGETjson()
            
            # Find all objects of the specified type
            hrList = []
            for key in response:
                if objType in key:
                    data = response[key]
                    if data != "untracked":
                        # Process the data to create hyperrectangle
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
                                if "Target" in objType:
                                    hr = "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{0.0,0.8}}".format(
                                        x_min, x_max, y_min, y_max)
                                else:  # Obstacle
                                    hr = "{{{0:.4f},{1:.4f}}},{{{2:.4f},{3:.4f}}},{{-3.2,3.2}},{{-2.1,2.1}}".format(
                                        x_min, x_max, y_min, y_max)
                                
                                hrList.append([key, hr])
                        except Exception as e:
                            print("Error processing data for " + key + ": " + str(e))
            
            return hrList
        except Exception as e:
            print("Error getting hyperrectangle data: " + str(e))
            return []

# Initialize symbolic controller with retries
def initialize_symbolic_controller(uri):
    """Initialize symbolic controller with retries"""
    print("Initializing symbolic controller with URI: " + uri)
    for attempt in range(MAX_RETRIES):
        try:
            controller = RemoteSymbolicController(uri)
            print("Successfully initialized symbolic controller")
            return controller
        except Exception as e:
            print("Error initializing symbolic controller (attempt {0}/{1}): {2}".format(
                attempt+1, MAX_RETRIES, str(e)))
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise
    raise Exception("Failed to initialize symbolic controller after " + str(MAX_RETRIES) + " attempts")

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

def stack_hrs(hrList):
    """Stack hyperrectangles with error handling"""
    if not hrList:
        return ""
        
    ret_str = ""
    idx = 0
    l = len(hrList)
    for name_hr in hrList:
        ret_str += name_hr[1]
        if idx < l-1:
             ret_str += "|"
        idx += 1
    return ret_str

def new_control_task(loc_server, logger):
    """Initialize control task"""
    global localization_server
    global sym_control
    
    print("Initializing new control task")
    
    # Create our robust localization server interface
    try:
        localization_server = RobustLocalizationServerInterface("http://" + LOCALIZATION_SERVER_IPPORT + "/OptiTrackRestServer")
        print("Successfully created localization server interface")
    except Exception as e:
        logger.log("Error creating localization server interface: " + str(e))
        return True  # Error occurred
    
    # Initialize symbolic controller
    try:
        sym_control = initialize_symbolic_controller(SYMCONTROL_SERVER_URI)
    except Exception as e:
        logger.log("Error initializing symbolic controller: " + str(e))
        return True  # Error occurred
    
    # Force garbage collection
    gc.collect()
    
    return False  # No error

def get_next_action(last_action, new_actions, state, logger):
    """Get next action with error handling"""
    try:
        # Convert state string to list of floats
        state = list(map(float, state.replace("(","").replace(")","").split(',')))
        
        new_actions_conc = []
        good_candidate_idx = 0
        idx = 0
        
        for action_str in new_actions:
            if not action_str or action_str.strip() == "":
                logger.log("Skipping empty action at index " + str(idx))
                idx += 1
                continue
                
            try:
                new_action = action_str.replace("(","").replace(")","").split(',')
                
                if (len(new_action) != 2):
                    logger.log("Found invalid action in the list of actions: " + action_str)
                    idx += 1
                    continue

                new_action = [DeepRacer.unmap_angle(float(new_action[0])), DeepRacer.unmap_trottle(float(new_action[1]))]
                new_actions_conc.append(new_action)

                # selection criterion: first action with same direction as last action
                if last_action != None:
                    if last_action[1]>0 and new_action[1]>0:
                        good_candidate_idx = idx
                        break
                    if last_action[1]<0 and new_action[1]<0:
                        good_candidate_idx = idx
                        break
            except Exception as e:
                logger.log("Error processing action '" + action_str + "': " + str(e))
                
            idx += 1
        
        # Check if we have any valid actions
        if not new_actions_conc:
            logger.log("No valid actions found")
            return "stop"
            
        # Select the best action
        selected_action = new_actions_conc[min(good_candidate_idx, len(new_actions_conc)-1)]
        return selected_action
        
    except Exception as e:
        logger.log("Error in get_next_action: " + str(e))
        return "stop"

def get_control_action(s, logger):
    """Get control action with comprehensive error handling"""
    global curr_target
    global target_vals
    global hrListTar
    global last_action
    global localization_server
    global sym_control

    try:
        # Normalize theta value to be within acceptable range
        if len(s) >= 4:
            original_theta = s[3]
            s[3] = normalize_theta(s[3])
            if abs(original_theta - s[3]) > 0.001:
                logger.log("Normalized theta from {0} to {1}".format(original_theta, s[3]))

        # Prepare targets/obstacles
        logger.log("Getting targets and obstacles...")
        hrListTar = localization_server.get_hyper_rec_str("Target")
        
        if not hrListTar:
            logger.log("No targets found in the scene")
            return [True, "stop"]
            
        target_str = stack_hrs(hrListTar)
        if target_str == "":
            logger.log("Empty target string")
            return [True, "stop"]
            
        obstacles_str = stack_hrs(localization_server.get_hyper_rec_str("Obstacle"))
        logger.log("Found {0} targets and obstacles".format(len(hrListTar)))

        # Set target
        if curr_target >= len(hrListTar):
            logger.log("Current target index {0} is out of range (0-{1})".format(curr_target, len(hrListTar)-1))
            curr_target = 0
            
        target_str = hrListTar[curr_target][1]
        target_vals = str(target_str).replace('{','').replace('}','')
        target_vals = target_vals.split(',')
        
        logger.log("Using target #{0}: {1}".format(curr_target, hrListTar[curr_target][0]))

        # Are we already in a target?
        try:
            if (s[0] >= float(target_vals[0]) and s[0] <= float(target_vals[1])) and \
               (s[1] >= float(target_vals[2]) and s[1] <= float(target_vals[3])):
                logger.log("Reached the target set #{0}. S={1}".format(curr_target, str(s)))
                curr_target += 1
                if curr_target == len(hrListTar):
                    curr_target = 0
                return [True, "stop"]
        except Exception as e:
            logger.log("Error checking if in target: " + str(e))
            # Continue execution - don't return yet

        # Format state for controller
        s_send = str(s).replace('[','(').replace(']',')')
        logger.log("Sending state: " + s_send)
        
        # Synthsize a controller + get actions
        logger.log("Synthesizing controller and getting actions...")
        
        # Force garbage collection before network operations
        gc.collect()
        
        try:
            u_psi_list = sym_control.synthesize_controller_get_actions(obstacles_str, target_str, s_send)
            
            if not u_psi_list or u_psi_list.strip() == "":
                logger.log("Empty response from controller")
                logger.log("This may be due to state being outside controller domain")
                return [True, "stop"]
                
            logger.log("Received actions: " + u_psi_list[:100] + "...")
        except Exception as e:
            logger.log("Controller synthesis / action collection failed: " + str(e))
            
            # Check if we need to reinitialize the controller
            if "mode" in str(e) or "connection" in str(e).lower():
                logger.log("Attempting to reinitialize symbolic controller...")
                try:
                    sym_control = initialize_symbolic_controller(SYMCONTROL_SERVER_URI)
                    logger.log("Successfully reinitialized symbolic controller")
                except Exception as e2:
                    logger.log("Failed to reinitialize controller: " + str(e2))
            
            return [True, "stop"]

        # Selecting one action
        logger.log("Selecting best action...")
        actions_list = u_psi_list.replace(" ","").split('|')
        if len(actions_list) == 0:
            logger.log("The controller returned no actions")
            return [True, "stop"]

        action = get_next_action(last_action, actions_list, s_send, logger)
        if action == "stop":
            return [True, "stop"]
            
        last_action = action
        logger.log("Selected action: " + str(action))
        
        # Force garbage collection after completing a cycle
        gc.collect()
        
        return [True, action]
        
    except Exception as e:
        logger.log("UNEXPECTED ERROR in get_control_action: " + str(e))
        logger.log(traceback.format_exc())
        return [True, "stop"]

def after_control_task(logger):
    """Clean up after control task"""
    # Force garbage collection
    gc.collect()
    return False

# Signal handler
def sig_handler(signal_received, frame):
    print("Exiting gracefully...")
    # Force garbage collection before exit
    gc.collect()
    exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal(SIGINT, sig_handler)
    
    print("\n=== DeepRacer Controller - Robust Python 2.7 Version ===")
    print("This controller includes improved error handling and memory management")
    print("Theta range: [{0}, {1}]".format(THETA_MIN, THETA_MAX))
    print("Max retries: {0}, Retry delay: {1}s".format(MAX_RETRIES, RETRY_DELAY))
    
    # Force initial garbage collection
    gc.collect()
    
    # Create controller and start
    dr_controller = DeepRacerController(tau, ROBOT_NAME, LOCALIZATION_SERVER_IPPORT, 
                                       new_control_task, get_control_action, after_control_task)
    
    # Start the controller
    dr_controller.spin()
