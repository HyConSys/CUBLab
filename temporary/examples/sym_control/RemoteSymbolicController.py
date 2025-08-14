import RESTApiClient
import time

SLEEP_TIME = 0.005

class RemoteSymbolicController():
    def __init__(self, url):
        #url is compute server
        self.rest_client = RESTApiClient.RESTApiClient(url)

    # get the mode of the server
    def getMode(self):
        return self.rest_client.restGETjson()["mode"]

    # request a controller syntehsis operation from a SYM-Control server
    def synthesize_controller(self, obstacles_str, target_str, is_last_req):
        # wait for synth-mode
        mode = ""
        while mode != "collect_synth":
            mode = self.getMode()

        # put request
        if is_last_req:
            is_last_synth_request = "true"
        else:
            is_last_synth_request = "false"  

        json_data = {
            "target_set":target_str,
            "obst_set":obstacles_str,
            "is_last_synth_request":is_last_synth_request,
            "is_synth_requested":"true"
        }
        self.rest_client.restPUTjson(json_data)

        # wait for distribute_control => the synthesis is done
        mode = ""
        while mode != "distribute_control":
            mode = self.getMode()

    # given a state, get a list of controls for a synthesized controller
    def get_controls(self, state_str, is_last_request):
        # wait for synth-mode
        mode = ""
        while mode != "distribute_control":
            mode = self.getMode()

        # put action request
        if is_last_request:
            is_last_control_request = "true"
        else:
            is_last_control_request = "false"

        json_data = {
            "current_state":state_str,
            "is_control_requested":"true",
            "is_last_control_request":is_last_control_request
        }
        self.rest_client.restPUTjson(json_data)

        # wait for synth-mode
        data = ""
        is_control_ready = ""
        while is_control_ready != "true":
            data =self.rest_client.restGETjson()
            is_control_ready = data["is_control_ready"]
        
        # acknowledge
        json_data = {"is_control_recieved":"true"}
        self.rest_client.restPUTjson(json_data)

        # extract actions
        return data["actions_list"]

    # a combined realtime version of the above two functions
    def synthesize_controller_get_actions(self, obstacles_str, target_str, state_str):
        # wait for synth-mode
        mode = self.getMode()
        while mode != "collect_synth":
            time.sleep(SLEEP_TIME)
            mode = self.getMode()

        json_data = {
            "target_set":target_str,
            "obst_set":obstacles_str,
            "is_last_synth_request":"false",
            "is_synth_requested":"true",
            "current_state":state_str,
            "is_control_requested":"true",
            "is_last_control_request":"true"
        }
        #sending deepracer info to compute server only when its in collect_synth mode
        self.rest_client.restPUTjson(json_data)

        # wait for control ready
        data = ""
        is_control_ready = ""
        #waiting got is_control_ready to return true, and then we acknowlede we recieved it and extract action list
        while is_control_ready != "true":
            time.sleep(SLEEP_TIME)
            data =self.rest_client.restGETjson()
            is_control_ready = data["is_control_ready"]
        
        # acknowledge
        json_data = {"is_control_recieved":"true"}
        self.rest_client.restPUTjson(json_data)

        # extract actions
        return data["actions_list"]

