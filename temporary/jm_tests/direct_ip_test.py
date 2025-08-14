#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
import socket
import traceback

try:
    # Python 3
    import urllib.request as urllib_request
    from urllib.error import URLError
except ImportError:
    # Python 2
    import urllib2 as urllib_request
    from urllib2 import URLError

# Configuration
OPTITRACK_IP = "192.168.1.194"
OPTITRACK_PORT = "12345"
OPTITRACK_URL = "http://{0}:{1}/OptiTrackRestServer".format(OPTITRACK_IP, OPTITRACK_PORT)

def ping_host(host):
    """Simple ping test using socket connection"""
    try:
        print("Testing direct socket connection to {0}...".format(host))
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Attempt to connect
        result = sock.connect_ex((host, 80))
        if result == 0:
            print("SUCCESS: Socket connection to {0} succeeded".format(host))
            return True
        else:
            print("FAILED: Socket connection to {0} failed with code {1}".format(host, result))
            return False
    except Exception as e:
        print("ERROR: Socket connection test failed: {0}".format(str(e)))
        return False
    finally:
        sock.close()

def test_direct_connection():
    """Test direct connection to OptiTrack server using urllib"""
    print("\n=== Testing Direct Connection to OptiTrack ===")
    print("URL: " + OPTITRACK_URL)
    
    # First, try to ping the host
    print("\nTesting basic network connectivity...")
    if not ping_host(OPTITRACK_IP):
        print("WARNING: Basic connectivity test failed")
    
    # Try with different timeout values
    timeouts = [5, 10, 30, 60]
    
    for timeout in timeouts:
        print("\nAttempting connection with {0} second timeout...".format(timeout))
        start_time = time.time()
        
        try:
            # Create a direct request
            request = urllib_request.Request(OPTITRACK_URL)
            response = urllib_request.urlopen(request, timeout=timeout)
            
            elapsed = time.time() - start_time
            print("Response received in {0:.2f} seconds".format(elapsed))
            
            # Read the response
            content = response.read()
            
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
        
        except URLError as e:
            elapsed = time.time() - start_time
            print("URLError after {0:.2f} seconds: {1}".format(elapsed, str(e)))
        
        except Exception as e:
            elapsed = time.time() - start_time
            print("Error after {0:.2f} seconds: {1}".format(elapsed, str(e)))
            print("Traceback:")
            traceback.print_exc()
    
    print("\nFAILED: Could not connect to OptiTrack server with any timeout")
    return False

if __name__ == "__main__":
    test_direct_connection()
