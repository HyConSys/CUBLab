#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .RESTApiClient import RESTApiClient

class LocalizationServerInterface:
    """Interface to the OptiTrack localization server, updated for Python 3.8"""
    
    def __init__(self, url):
        """Initialize with the server URL"""
        self.rest_client = RESTApiClient(url)

    def getRigidBodyState(self, rbName):
        """Get the state of a rigid body by name"""
        response = self.rest_client.restGETjson(f"?RigidBody={rbName}")
        return response[rbName]

    def get_hyper_rec_str(self, item_type):
        """Get hyperrectangle strings for objects of the given type
        
        This follows the specific format required by the pFaces server:
        - First part uses real coordinates from OptiTrack
        - Second part (after | separator) uses hardcoded coordinates: {2.0,3.0},{2.0,3.0}
        """
        response = self.rest_client.restGETjson()
        return_list = []

        # Process each item in the response
        for item_name, item_data in response.items():
            is_passed = False
            if item_data != "untracked":
                try:
                    values = item_data.split(',')
                    x = float(values[1].strip())
                    y = float(values[2].strip())
                    width = float(values[5].strip())
                    height = float(values[6].strip())

                    # Calculate bounding box coordinates
                    x_min = x - width/2
                    x_max = x + width/2
                    y_min = y - height/2
                    y_max = y + height/2

                    if "Target" in item_name and "Target" == item_type:
                        # Format for targets with specific theta and velocity ranges
                        x_1 = f"{x_min:.4f}"
                        x_2 = f"{x_max:.4f}"
                        y_1 = f"{y_min:.4f}"
                        y_2 = f"{y_max:.4f}"
                        theta_v = "{-3.2,3.2},{0.0,0.8}"
                        
                    elif "Obstacle" in item_name and "Obstacle" == item_type:
                        # Format for obstacles with specific theta and velocity ranges
                        x_1 = f"{x_min:.4f}"
                        x_2 = f"{x_max:.4f}"
                        y_1 = f"{y_min:.4f}"
                        y_2 = f"{y_max:.4f}"
                        theta_v = "{-3.2,3.2},{-2.1,2.1}"
                        
                    else:
                        is_passed = True
                        continue
                        
                    if not is_passed:
                        # Create the hyperrectangle string with the required format
                        return_string = f"{{{x_1},{x_2}}},{{{y_1},{y_2}}},{theta_v}"
                        return_list.append((item_name, return_string))
                        
                except Exception as e:
                    print(f"Error processing {item_name}: {str(e)}")
                    continue
                    
        return return_list
