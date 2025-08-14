#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
import httplib2
import traceback

# Configuration
LOCALIZATION_SERVER_URL = "http://192.168.1.194:12345/OptiTrackRestServer"

def test_optitrack_connection():
    """Test direct connection to OptiTrack server"""
    print("\n=== Testing OptiTrack Connection ===")
    print("URL: " + LOCALIZATION_SERVER_URL)
    
    # Try with different timeout values
    timeouts = [5, 10, 30, 60, 120]
    
    for timeout in timeouts:
        print("\nAttempting connection with {0} second timeout...".format(timeout))
        start_time = time.time()
        
        try:
            # Create a new HTTP connection
            http = httplib2.Http(timeout=timeout)
            print("Sending request...")
            response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
            
            elapsed = time.time() - start_time
            print("Response received in {0:.2f} seconds".format(elapsed))
            
            if response.status != 200:
                print("HTTP Error: Status {0}".format(response.status))
                continue
                
            # Try to parse JSON
            try:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                data = json.loads(content)
                
                # Check for expected objects
                objects_found = []
                for key in data:
                    if data[key] != "untracked":
                        objects_found.append(key)
                
                print("SUCCESS! Received valid JSON response")
                print("Found {0} tracked objects: {1}".format(len(objects_found), ", ".join(objects_found)))
                
                # Print first few characters of response
                print("Response preview: " + str(content)[:100] + "...")
                
                # This timeout worked, so we can stop testing
                print("\nSUCCESS: Connection with {0} second timeout worked".format(timeout))
                return True
                
            except ValueError as e:
                print("JSON parsing error: " + str(e))
                print("Response content: " + str(content)[:100] + "...")
        
        except Exception as e:
            elapsed = time.time() - start_time
            print("Error after {0:.2f} seconds: {1}".format(elapsed, str(e)))
            print("Traceback:")
            traceback.print_exc()
        
        finally:
            # Clean up HTTP connection
            try:
                http.clear()
            except:
                pass
    
    print("\nFAILED: Could not connect to OptiTrack server with any timeout")
    return False

if __name__ == "__main__":
    test_optitrack_connection()
