import time
import math
from signal import signal, SIGINT
from sys import exit
from sys import path

# insert src into script path
path.insert(1, '../../src')

import DeepRacer
from DeepRacerController import DeepRacerController
from RemoteSymbolicController import RemoteSymbolicController
from Logger import Logger

STOP_AFTER_LAST_TARGET = False
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME
curr_target = 0
target_vals = []
hrListTar = []
tau = 0.0
sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
localization_server = []

# Theta range limits based on testing
THETA_MIN = -1.7  # Determined through testing
THETA_MAX = 1.7   # Determined through precise testing (values > 1.7 fail)

# making a dummy request to close the current ccontrol-requests session
def send_dummy_getcontrol_req():
    sym_control.get_controls("(0,0,0,0)", True) 

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

def new_control_task(loc_server, logger):
    global localization_server
    localization_server = loc_server
    return False

def get_next_action(last_action, new_actions, state, logger):
    state = list(map(float, state.replace("(","").replace(")","").split(',')))
    new_actions_conc = []
    good_candidate_idx = 0
    idx = 0
    for action_str in new_actions:
        new_action = action_str.replace("(","").replace(")","").split(',')
        
        if (len(new_action) != 2):
            logger.log("Found invalid action in the list of actions.")
            return "stop"

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

        idx += 1
    
    if not new_actions_conc:
        logger.log("No valid actions found.")
        return "stop"
        
    return new_actions_conc[good_candidate_idx]
    

last_action = None
def get_control_action(s, logger):
    global curr_target
    global target_vals
    global hrListTar
    global last_action
    global localization_server

    # Normalize theta value to be within acceptable range
    if len(s) >= 4:
        original_theta = s[3]
        s[3] = normalize_theta(s[3])
        if abs(original_theta - s[3]) > 0.001:
            logger.log("Normalized theta from {0} to {1}".format(original_theta, s[3]))

    # prepare targets/obstacles
    try:
        hrListTar = localization_server.get_hyper_rec_str("Target")
        target_str = stack_hrs(hrListTar)
        obstacles_str = stack_hrs(localization_server.get_hyper_rec_str("Obstacle"))
        if (target_str == ""):
            logger.log("Exiting as no targets in the scene.")
            return [True, "stop"]
    except Exception as e:
        logger.log("Error getting targets/obstacles: " + str(e))
        return [True, "stop"]

    # set target
    try:
        target_str = hrListTar[curr_target][1]    
        target_vals = str(target_str).replace('{','').replace('}','')
        target_vals = target_vals.split(',')
    except Exception as e:
        logger.log("Error setting target: " + str(e))
        return [True, "stop"]

    # are we already in a target ?
    try:
        if (s[0] >= float(target_vals[0]) and s[0] <= float(target_vals[1])) and (s[1] >= float(target_vals[2]) and s[1] <= float(target_vals[3])):
            logger.log("Reached the target set #" + str(curr_target) + ". S=" + str(s))
            curr_target += 1
            if curr_target == len(hrListTar):
                curr_target = 0
            return [True, "stop"]
    except Exception as e:
        logger.log("Error checking if in target: " + str(e))
        return [True, "stop"]

    # synthsize a controller + get actions
    try:
        s_send = str(s).replace('[','(').replace(']',')')
        logger.log("Sending state: " + s_send)
        u_psi_list = sym_control.synthesize_controller_get_actions(obstacles_str, target_str, s_send)
        
        if not u_psi_list or u_psi_list.strip() == "":
            logger.log("Empty response from controller. This may be due to state being outside controller domain.")
            return [True, "stop"]
            
    except Exception as e:
        logger.log("Controller synthesis / action collection failed: " + str(e))
        logger.log("This may be due to theta value being outside acceptable range or server connection issues.")
        return [True, "stop"]

    # selecting one action
    try:
        actions_list = u_psi_list.replace(" ","").split('|')
        if len(actions_list) == 0:
            logger.log("The controller returned no actions.")
            return [True, "stop"]

        action = get_next_action(last_action, actions_list, s_send, logger)
        if action == "stop":
            return [True, "stop"]
            
        last_action = action
        return [True, action]
    except Exception as e:
        logger.log("Error selecting action: " + str(e))
        return [True, "stop"]

def after_control_task(logger):
    return False

# signal handler
def sig_handler(signal_received, frame):    
    exit(0)

if __name__ == "__main__":
    signal(SIGINT, sig_handler)
    # SampleTime, DeepRacerName, LocalizationServerIPPort, cb_new_control_task, cb_get_control_action, cb_after_control_task
    dr_controller = DeepRacerController(tau, ROBOT_NAME, LOCALIZATION_SERVER_IPPORT, new_control_task, get_control_action, after_control_task)
    dr_controller.spin()
