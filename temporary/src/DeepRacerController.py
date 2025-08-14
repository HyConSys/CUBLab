import time
from MotionControls import MotionControls
from LocalizationServerInterface import LocalizationServerInterface
from Logger import Logger
from StoreRun_Logger import StoreRun_Logger

class DeepRacerController():
    def __init__(self, SampleTime, DeepRacerName, LocalizationServerIPPort, cb_new_control_task, cb_get_control_action, cb_after_control_task):
        
        # arena dimensions : measured using a single marker in Motive/Cameras
        self.ARENA_UB = [2.129, 2.204]
        self.ARENA_LB = [-2.166, -2.147]

        # sensing and control objects
        self.DeepRacerName = DeepRacerName
        self.motion_control = MotionControls()
        self.loc_server = LocalizationServerInterface("http://" + LocalizationServerIPPort + "/OptiTrackRestServer")

        # a logger
        self.logger = Logger()
        self.logger_states = StoreRun_Logger() #added this

        # callbacks
        self.new_control_task = cb_new_control_task
        self.get_control_action = cb_get_control_action
        self.after_control_task = cb_after_control_task

        # others
        self.tau = SampleTime


    def spin(self):
        # the high-level planning loop
        planningloop_index = 0
        while(True):

            should_exit = self.new_control_task(self.loc_server, self.logger)
            if should_exit:
                break

            # the motion-control loop
            controlloop_index = 0
            while(True):
                
                # get the DR state (t, x, y, theta, v)
                get_s_time_start = time.time()
                s_str = self.loc_server.getRigidBodyState(self.DeepRacerName) 
                get_s_time_end = time.time()
                get_state_total_time = (get_s_time_end - get_s_time_start) 

                # stop controls if..
                if s_str == "untracked":
                    self.motion_control.stop()
                    self.logger.log("Stopped due to an untracked state.")
                    should_exit = True
                    break

                # extract state of DR
                s_split = s_str.split(',')
                s = [float(s_split[1]), float(s_split[2]), float(s_split[3]), float(s_split[4])]
                
                self.logger_states.log("Printing deepracer state: " + s) #added this

                # check if out of bounds on x
                if s[0] > self.ARENA_UB[0] or s[0] < self.ARENA_LB[0]:
                    self.motion_control.stop()
                    self.logger.log("Stopped due to an out of range state (X). s=" + str(s))
                    should_exit = True
                    break

                # check if out of bounds on y
                if s[1] > self.ARENA_UB[1] or s[1] < self.ARENA_LB[1]: 
                    self.motion_control.stop()
                    self.logger.log("Stopped due to an out of range state (Y). S = " + str(s))
                    should_exit = True
                    break

                control_time_start = time.time()
                try:
                    (last_controlloop, action) = self.get_control_action(self.loc_server, s, self.logger, self.logger_states) #added parameter
                except:
                    self.logger.log("Stopping due to error in getting control ations.")
                    self.motion_control.stop()
                    should_exit = True
                    break
                control_time_end = time.time()
                control_total_time = (control_time_end - control_time_start) # measuring how long time request takes

                # stop if no input is received
                if action == None or action == "" or action == []:
                    self.motion_control.stop()
                    self.logger.log("Stopped as we received no control action.")
                    should_exit = True
                    break
        
                # move the car
                if action == "stop":
                    self.motion_control.stop()
                else:
                    self.motion_control.drive(action[0], action[1])

                # for logging every loop: time, in, out, action, loop index
                controlloop_index += 1
                total_time = control_total_time + get_state_total_time

                # writing information to log files
                self.logger.log("Loop #" + str(planningloop_index) + "." + str(controlloop_index) + ": state_time=" + str(get_state_total_time) + ", control_time=" + str(control_total_time) + ", action=" + str(action))

                # tau=0.0 means no realtime window enformement/check
                # tau>0.0 means realtime window will be enforced/checked
                if self.tau > 0.0:
                    if total_time < self.tau:
                        time.sleep(self.tau - total_time)
                    else:
                        if total_time/self.tau > 2.5:
                            self.motion_control.stop()
                            self.logger.log("Stopped due excess violation of real-time deadline. Total time = " + str(total_time))
                            should_exit = True
                            break

                if last_controlloop:
                    break

            if should_exit:
                break

            should_exit = self.after_control_task(self.logger)
        
            if should_exit:
                break
            
            controlloop_index += 1



    def __del__(self):
        del self.motion_control
        del self.loc_server
