#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .RESTApiClient import RESTApiClient

class RemoteSymbolicController:
    """Remote Symbolic Controller for DeepRacer, updated for Python 3.8
    
    This class follows the exact pattern of the working synth_and_get.py example:
    1. Create a RemoteSymbolicController
    2. Call synthesize_controller with hyperrectangles
    3. Wait briefly for synthesis to complete
    4. Create a new RemoteSymbolicController instance
    5. Call get_controls with the state
    """
    
    def __init__(self, url):
        """Initialize with the server URL"""
        self.rest_client = RESTApiClient(url)
        
    def synthesize_controller(self, obstacles_str, target_str):
        """Synthesize a controller with the given obstacles and target
        
        This sets the pFaces server mode to collect_synth.
        """
        # Create the request payload
        request = {
            "mode": "collect_synth",
            "obstacles": obstacles_str,
            "target": target_str
        }
        
        # Send the request to the server
        response = self.rest_client.restPUTjson(request)
        return response
        
    def get_controls(self, state_str):
        """Get controls for the given state
        
        This sets the pFaces server mode to distribute_control.
        """
        # Create the request payload
        request = {
            "mode": "distribute_control",
            "state": state_str
        }
        
        # Send the request to the server
        response = self.rest_client.restPUTjson(request)
        
        # Extract actions from the response
        if "actions" in response:
            return response["actions"]
        else:
            return []
