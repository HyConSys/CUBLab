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

STOP_AFTER_LAST_TARGET = False
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME
curr_target = 0
target_vals = []
hrListTar = []
tau = 0.25
sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)

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

def new_control_task(loc_server, logger):
    global curr_target
    global target_vals
    global hrListTar

    # prepare targets/obstacles
    hrListTar = loc_server.get_hyper_rec_str("Target")
    target_str = stack_hrs(hrListTar)
    obstacles_str = stack_hrs(loc_server.get_hyper_rec_str("Obstacle"))
    if (target_str == ""):
        logger.log("Exiting as no targets in the scene.")
        return True

    # set target
    target_str = hrListTar[curr_target][1]    
    target_vals = str(target_str).replace('{','').replace('}','')
    target_vals = target_vals.split(',')

    # make a synthsize controller request and wait for the controller
    try:
        mode = sym_control.getMode()
        if mode != "distribute_control":
            logger.log("Requesting a control synthesis ...")
            logger.log("Obstacles: " + obstacles_str)
            logger.log("Target: " + target_str)
            sym_control.synthesize_controller(obstacles_str, target_str, False)
            logger.log("Controller synthesis done.")
        else:
            logger.log("Controller synthesis skipped as we found the server ready for control-requests.")
        return False
    except:
        logger.log("Controller synthesis Failed.")
        return True


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
    
    return new_actions_conc[good_candidate_idx]
    

last_action = None
def get_control_action(loc_server, s, logger):
    global curr_target
    global target_vals
    global hrListTar
    global last_action

    if (s[0] >= float(target_vals[0]) and s[0] <= float(target_vals[1])) and (s[1] >= float(target_vals[2]) and s[1] <= float(target_vals[3])):
        send_dummy_getcontrol_req()
        logger.log("Reached the target set #" + str(curr_target) + ". S=" + str(s))
        return [True, "stop"]

    # prepare targets/obstacles
    hrListTar = loc_server.get_hyper_rec_str("Target")
    target_str = stack_hrs(hrListTar)
    obstacles_str = stack_hrs(loc_server.get_hyper_rec_str("Obstacle"))
    if (target_str == ""):
        logger.log("Exiting as no targets in the scene.")
        return True

    # set target
    target_str = hrListTar[curr_target][1]    
    target_vals = str(target_str).replace('{','').replace('}','')
    target_vals = target_vals.split(',')

    s_send = str(s).replace('[','(').replace(']',')')
    #logger.log("State = " + s_send)

    try:
        u_psi_list = sym_control.synthesize_controller_get_actions(obstacles_str, target_str, s_send) 
    except:
        logger.log("Failed to get actions list from the sym-control server.")
        return [True, None]

    # electing one action
    actions_list = u_psi_list.replace(" ","").split('|')
    if len(actions_list) == 0:
        send_dummy_getcontrol_req()
        logger.log("The controller returned no actions.")
        return [True, "stop"]

    action = get_next_action(last_action, actions_list, s_send, logger)
    last_action = action
    return [False, action]

def after_control_task(logger):
    global curr_target
    global target_vals
    global hrListTar

    should_exit = False
    curr_target += 1 # increase target index
    if curr_target == len(hrListTar):
        logger.log("Reached the last target.")
        if STOP_AFTER_LAST_TARGET:
            should_exit = True
        else:
            logger.log("Will start again from the first target.")
            curr_target = 0
    else:
        logger.log("Switched to target set #" + str(curr_target))

    return should_exit

# signal handler
def sig_handler(signal_received, frame):    
    exit(0)

if __name__ == "__main__":
    signal(SIGINT, sig_handler)
    dr_controller = DeepRacerController(tau, ROBOT_NAME, LOCALIZATION_SERVER_IPPORT, new_control_task, get_control_action, after_control_task)
    dr_controller.spin()
    
    
