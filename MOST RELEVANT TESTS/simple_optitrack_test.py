#!/usr/bin/env python3
import sys
import os
import json
import requests
import time

# The URL of the OptiTrack server
OPTITRACK_URL = "http://192.168.1.194:12345/OptiTrackRestServer"

def main():
    print("Simple OptiTrack Test")
    print(f"Connecting to: {OPTITRACK_URL}")
    
    try:
        # Make a direct request to the OptiTrack server
        response = requests.get(OPTITRACK_URL, timeout=5)
        
        if response.status_code == 200:
            print("Connection successful!")
            data = response.json()
            
            print("\nAvailable objects:")
            for key in data:
                value = data[key]
                print(f"  {key}: {value}")
            
            # Check for specific objects
            required_objects = ["DeepRacer1", "Obstacle4", "Target4"]
            for obj in required_objects:
                if obj in data:
                    if data[obj] == "untracked":
                        print(f"\n{obj} is present but UNTRACKED")
                    else:
                        print(f"\n{obj} is TRACKED: {data[obj]}")
                        
                        # Parse values
                        values = data[obj].split(',')
                        if len(values) >= 7:
                            x = float(values[1].strip())
                            y = float(values[2].strip())
                            theta = float(values[3].strip())
                            v = float(values[4].strip())
                            width = float(values[5].strip())
                            height = float(values[6].strip())
                            
                            print(f"  Parsed data:")
                            print(f"  Position: X={x}, Y={y}")
                            print(f"  Orientation/Velocity: Theta={theta}, V={v}")
                            print(f"  Dimensions: Width={width}, Height={height}")
                            
                            # Calculate bounding box for hyperrectangle
                            x_min = x - width/2
                            x_max = x + width/2
                            y_min = y - height/2
                            y_max = y + height/2
                            
                            print(f"  Bounding box: X=[{x_min:.4f},{x_max:.4f}], Y=[{y_min:.4f},{y_max:.4f}]")
                else:
                    print(f"\n{obj} is MISSING")
            
        else:
            print(f"Error: Server returned status code {response.status_code}")
            
    except Exception as e:
        print(f"Error connecting to server: {str(e)}")
    
if __name__ == "__main__":
    main()
