from remote_pdb import RemotePdb
import logging
import time
import math
from signal import signal, SIGINT
from sys import exit
from sys import path
# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("output.log"),
                              logging.StreamHandler()])
path.insert(1, '../../src')


import DeepRacer
from RemoteSymbolicController import RemoteSymbolicController
from DeepRacerController import DeepRacerController
logging.info("Imported DeepRacer and RemoteSymbolicController")




STOP_AFTER_LAST_TARGET = False
ROBOT_NAME = "DeepRacer1"
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
COMPUTE_SERVER_IPPORT = "192.168.1.144:12345"
#COMPUTE_SERVER_IPPORT = "192.168.1.144:12345" (old ip before ethernet port change)

SYMCONTROL_SERVER_URI = "http://" + COMPUTE_SERVER_IPPORT + "/pFaces/REST/dictionary/"+ROBOT_NAME
curr_target = 0
target_vals = []
hrListTar = []
tau = 0.0
sym_control = RemoteSymbolicController(SYMCONTROL_SERVER_URI)
localization_server = []

# making a dummy request to close the current ccontrol-requests session
def send_dummy_getcontrol_req():
    print("Sending request to compute server: {COMPUTE_SERVER_IPPORT}")
    sym_control.get_controls("(0,0,0,0)", True) 
    print("Received response from compute server: ")

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
    
    return new_actions_conc[good_candidate_idx]
    

last_action = None
def get_control_action(s, logger,logger_states): #added paramater
    global curr_target
    global target_vals
    global hrListTar
    global last_action
    global localization_server


    # prepare targets/obstacles
    hrListTar = localization_server.get_hyper_rec_str("Target")  #retrieving target info from localization server
    target_str = stack_hrs(hrListTar) 
    obstacles_str = stack_hrs(localization_server.get_hyper_rec_str("Obstacle"))  #retrieving obstacle info from localization server
    logger_states.log("Target coordinates: " + target_str) # added this
    logger_states.log("Obstacle coordinates: " + obstacles_str) # added this

    if (target_str == ""):
        logger.log("Exiting as no targets in the scene.")
        return True

    # set target
    target_str = hrListTar[curr_target][1]    
    target_vals = str(target_str).replace('{','').replace('}','')
    target_vals = target_vals.split(',')

    # are we already in a target ?
    if (s[0] >= float(target_vals[0]) and s[0] <= float(target_vals[1])) and (s[1] >= float(target_vals[2]) and s[1] <= float(target_vals[3])):
        logger.log("Reached the target set #" + str(curr_target) + ". S=" + str(s))
        curr_target += 1
        if curr_target == len(hrListTar):
            curr_target = 0
        return [True, "stop"]

    # synthsize a controller + get actions
    try:
        s_send = str(s).replace('[','(').replace(']',')')
        u_psi_list = sym_control.synthesize_controller_get_actions(obstacles_str, target_str, s_send)
        
    except:
        logger.log("Controller synthesis / action collection failed.")
        return [True, "stop"]

    # selecting one action
    actions_list = u_psi_list.replace(" ","").split('|')
    if len(actions_list) == 0:
        logger.log("The controller returned no actions.")
        return [True, "stop"]

    action = get_next_action(last_action, actions_list, s_send, logger)
    last_action = action
    return [True, action]

def after_control_task(logger):
    return False

# signal handler
def sig_handler(signal_received, frame):  
    logging.info("SIGINT received. Exiting...")
    exit(0)

if __name__ == "__main__":
    signal(SIGINT, sig_handler)
    dr_controller = DeepRacerController(tau, ROBOT_NAME, LOCALIZATION_SERVER_IPPORT, new_control_task, get_control_action, after_control_task)
    dr_controller.spin()

    
