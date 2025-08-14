import requests
import socket
import time
import ast
import re
import rospy
from std_msgs.msg import String
from ctrl_pkg.msg import ServoCtrlMsg

GPS_SERVER_NAME = "CUBLabMediaServer"
RROBOT_UNTRACKED_LABEL = "untarcked"
ROBOT_NAME = 'DeepRacer1'
SAMPLE_TIME = 0.5
STOP_ACTION = [0.0, 0.0]
OBSTACLE_WIDTH = 2.1
OBSTACLE_HEIGHT = 0.4
TARGET_WIDTH = 0.6
TARGET_HEIGHT = 0.6

def post_robot_controls(pub_manual_drive, action):
    msg = ServoCtrlMsg()
    msg.angle    = action[0]
    msg.throttle = action[1]
    pub_manual_drive.publish(msg)

def extract_robot_state(robot_name, gps_data):
    regex =  '\"' + robot_name + '\":\"([^\"]+)\"'
    state_str = re.findall(regex, gps_data)[0]
    if state_str == RROBOT_UNTRACKED_LABEL:
        return RROBOT_UNTRACKED_LABEL
    state_str_list = state_str.split(',')
    return list(map(float, state_str_list))

def get_robot_state(robot_name):
    server_ip = socket.gethostbyname(GPS_SERVER_NAME)
    response = requests.get("http://" + server_ip + ":12345/OptiTrackRestServer")
    gps_data = str(response.json())
    return extract_robot_state(robot_name, gps_data)

expected_action_index = 0
ready_for_new_control_loop = True
pub_manual_drive = []
def new_action_callback(data):
    global expected_action_index
    global ready_for_new_control_loop
    global pub_manual_drive
    action_pack = ast.literal_eval(data.data)

    actions_list = []
    if action_pack:
        pack_idx = action_pack[0]
        
        if pack_idx != expected_action_index:
            print('Waarning: we are out of orde here !')

        actions_list = action_pack[2]        

    if actions_list:
        post_robot_controls(pub_manual_drive, actions_list[0])
    else:
        post_robot_controls(pub_manual_drive, STOP_ACTION)

    ready_for_new_control_loop = True


def main():
    global expected_action_index
    global ready_for_new_control_loop
    global pub_manual_drive
    rospy.init_node('symcontrol_closedloop', anonymous=ANONYMITY)
    rospy.Subscriber('robot_controller_out_actions', String, new_action_callback)
    pub_mdl_state = rospy.Publisher('robot_controller_in_mdl_state', String)
    pub_manual_drive = rospy.Publisher('manual_drive', ServoCtrlMsg, queue_size=10)
    
    while True:
        if ready_for_new_control_loop:
            overhead_start = time.time()
            print('started a new control loop')
            # read state from the OptiTrackServer
            state = get_robot_state(ROBOT_NAME)
            if state == RROBOT_UNTRACKED_LABEL:
                print('Robot is untrackable in the arena ! Initiatte stopping ... ')
                state = ""

            # publish the state to the controller
            pub_mdl_state.publish(String(state))

            # smart wait for tau
            overhead_end = time.time()
            overhead = overhead_end - overhead_start
            time.sleep(SAMPLE_TIME - overhead)

            # sync
            expected_action_index += 1
            ready_for_new_control_loop = False
        
    
# MAIN
if __name__ == '__main__':
    main()
