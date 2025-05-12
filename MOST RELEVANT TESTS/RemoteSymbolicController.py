import sys
import os #these two prep for next line:

# include this path (current url, add .. to go up one level, then goes into src)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from RESTApiClient import RESTApiClient # prep for next line
#from src import RESTApiClient
import time
import json

SLEEP_TIME = 0.1

class RemoteSymbolicController:
    def __init__(self, url):
        self.rest_client = RESTApiClient.RESTApiClient(url)

    def getMode(self):
        return self.rest_client.restGETjson()["mode"]

    def synthesize_controller(self, obstacles_str, target_str, is_last_req):
        # Ensure any previous synth request is cleared
        self.rest_client.restPUTjson({
            "is_synth_requested": "false",
            "is_last_synth_request": "false"
        })
        time.sleep(0.2)

        is_last_synth_request = "true" if is_last_req else "false"

        json_data = {
            "target_set": target_str,
            "obst_set": obstacles_str,
            "is_last_synth_request": is_last_synth_request,
            "is_synth_requested": "true"
        }

        print("DEBUG: Sending synth request:")
        print(json.dumps(json_data, indent=2))

        self.rest_client.restPUTjson(json_data)

        print("DEBUG: Waiting for server to enter 'distribute_control' mode...")
        while True:
            mode = self.getMode()
            print("DEBUG: Current mode:", mode)
            if mode == "distribute_control":
                print("DEBUG: Synthesis complete.")
                break
            time.sleep(SLEEP_TIME)

    def get_controls(self, state_str, is_last_request):
        print("DEBUG: Waiting for 'distribute_control' mode to get controls...")
        while self.getMode() != "distribute_control":
            time.sleep(SLEEP_TIME)

        json_data = {
            "current_state": state_str,
            "is_control_requested": "true",
            "is_last_control_request": "true" if is_last_request else "false"
        }

        print("DEBUG: Sending control request:")
        print(json.dumps(json_data, indent=2))

        self.rest_client.restPUTjson(json_data)

        while True:
            data = self.rest_client.restGETjson()
            if data.get("is_control_ready") == "true":
                break
            time.sleep(SLEEP_TIME)

        self.rest_client.restPUTjson({"is_control_recieved": "true"})
        return data["actions_list"]

    def synthesize_controller_get_actions(self, obstacles_str, target_str, state_str):
        json_data = {
            "target_set": target_str,
            "obst_set": obstacles_str,
            "is_last_synth_request": "false",
            "is_synth_requested": "true",
            "current_state": state_str,
            "is_control_requested": "true",
            "is_last_control_request": "true"
        }

        print("DEBUG: Sending combined synth+control request:")
        print(json.dumps(json_data, indent=2))

        self.rest_client.restPUTjson(json_data)

        while True:
            data = self.rest_client.restGETjson()
            if data.get("is_control_ready") == "true":
                break
            time.sleep(SLEEP_TIME)

        self.rest_client.restPUTjson({"is_control_recieved": "true"})
        return data["actions_list"]
