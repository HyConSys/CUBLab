#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import traceback
import httplib2
import socket

# Simple path setup - assumes running from deepracer-utils/examples/sym_control
project_root = os.path.abspath(os.path.join(os.getcwd(), '../..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, src_path)      # Source files

# Try to import LocalizationServerInterface
try:
    from LocalizationServerInterface import LocalizationServerInterface
    print("Successfully imported LocalizationServerInterface")
except ImportError as e:
    # Alternative approach: manual import
    import imp
    loc_server_path = os.path.join(src_path, 'LocalizationServerInterface.py')
    loc_module = imp.load_source('LocalizationServerInterface', loc_server_path)
    LocalizationServerInterface = loc_module.LocalizationServerInterface
    print("Manually imported LocalizationServerInterface")

# Configuration
LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
LOCALIZATION_SERVER_URL = "http://{0}/OptiTrackRestServer".format(LOCALIZATION_SERVER_IPPORT)

def test_method_1():
    """Test using the same method as robust_controller_py27.py"""
    print("\n=== TEST METHOD 1: Using LocalizationServerInterface ===")
    print("URL: " + LOCALIZATION_SERVER_URL)
    
    try:
        print("Creating LocalizationServerInterface...")
        localization_server = LocalizationServerInterface(LOCALIZATION_SERVER_URL)
        
        print("Getting data from OptiTrack...")
        start_time = time.time()
        raw_data = localization_server.rest_client.restGETjson()
        elapsed = time.time() - start_time
        
        print("Request completed in {0:.2f} seconds".format(elapsed))
        
        if not raw_data:
            print("Error: OptiTrack server returned empty data")
            return False
            
        # Print found objects
        objects_found = []
        for key in raw_data:
            if raw_data[key] != "untracked":
                objects_found.append(key)
        
        if objects_found:
            print("Found {0} tracked objects: {1}".format(len(objects_found), ", ".join(objects_found)))
            print("\nSample data for first object:")
            print(raw_data[objects_found[0]])
            return True
        else:
            print("No tracked objects found")
            return False
            
    except Exception as e:
        print("Error: " + str(e))
        traceback.print_exc()
        return False

def test_method_2():
    """Test using direct httplib2 with short timeout"""
    print("\n=== TEST METHOD 2: Using direct httplib2 with short timeout ===")
    print("URL: " + LOCALIZATION_SERVER_URL)
    
    try:
        print("Creating HTTP connection with 3 second timeout...")
        http = httplib2.Http(timeout=3)  # Same timeout as RESTApiClient default
        
        print("Sending request...")
        start_time = time.time()
        response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
        elapsed = time.time() - start_time
        
        print("Request completed in {0:.2f} seconds".format(elapsed))
        print("HTTP Status: " + str(response.status))
        
        if response.status != 200:
            print("Error: HTTP status {0}".format(response.status))
            return False
        
        # Parse JSON response
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            data = json.loads(content)
            print("Successfully parsed JSON response")
            
            # Print objects found
            objects = []
            for key in data:
                if data[key] != "untracked":
                    objects.append(key)
            
            if objects:
                print("Found {0} tracked objects: {1}".format(len(objects), ", ".join(objects)))
                print("\nSample data for first object:")
                print(data[objects[0]])
                return True
            else:
                print("No tracked objects found")
                return False
            
        except ValueError as e:
            print("JSON parsing error: " + str(e))
            print("Response content: " + str(content)[:100] + "...")
            return False
            
    except socket.timeout:
        print("Connection timed out after 3 seconds")
        print("This is normal behavior for RESTApiClient - it would return an empty dict")
        return False
    except Exception as e:
        print("Error: " + str(e))
        traceback.print_exc()
        return False

def test_method_3():
    """Test using direct httplib2 with socket timeout handling"""
    print("\n=== TEST METHOD 3: Using direct httplib2 with socket timeout handling ===")
    print("URL: " + LOCALIZATION_SERVER_URL)
    
    try:
        print("Creating HTTP connection with 3 second timeout...")
        http = httplib2.Http(timeout=3)  # Same timeout as RESTApiClient default
        
        print("Sending request...")
        start_time = time.time()
        
        try:
            response, content = http.request(LOCALIZATION_SERVER_URL, method="GET")
            elapsed = time.time() - start_time
            
            print("Request completed in {0:.2f} seconds".format(elapsed))
            print("HTTP Status: " + str(response.status))
            
            if response.status != 200:
                print("Error: HTTP status {0}".format(response.status))
                return False
            
            # Parse JSON response
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            data = json.loads(content)
            print("Successfully parsed JSON response")
            
            # Print objects found
            objects = []
            for key in data:
                if data[key] != "untracked":
                    objects.append(key)
            
            if objects:
                print("Found {0} tracked objects: {1}".format(len(objects), ", ".join(objects)))
                return True
            else:
                print("No tracked objects found")
                return False
                
        except socket.timeout:
            elapsed = time.time() - start_time
            print("Connection timed out after {0:.2f} seconds".format(elapsed))
            print("This is normal behavior for RESTApiClient - it would return an empty dict")
            return False
            
    except Exception as e:
        print("Error: " + str(e))
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== OptiTrack Connection Test ===")
    print("This script tests different methods to connect to the OptiTrack server")
    print("Using the same methods as the working robust controllers")
    
    # Test all methods
    results = []
    
    print("\nTesting Method 1 (LocalizationServerInterface)...")
    results.append(("Method 1", test_method_1()))
    
    print("\nTesting Method 2 (Direct httplib2 with short timeout)...")
    results.append(("Method 2", test_method_2()))
    
    print("\nTesting Method 3 (Direct httplib2 with socket timeout handling)...")
    results.append(("Method 3", test_method_3()))
    
    # Print summary
    print("\n=== TEST RESULTS ===")
    for method, success in results:
        print("{0}: {1}".format(method, "SUCCESS" if success else "FAILED"))
