#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import socket

class RESTApiClient:
    """Modern RESTApiClient implementation using requests library for Python 3.8"""
    
    def __init__(self, url, timeout=3):
        """Initialize the REST API client with the given URL and timeout"""
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        # Don't use environment proxies to ensure direct connection
        self.session.trust_env = False
        print(f"Created RESTApiClient with URL: {url}, timeout: {timeout}s")
    
    def restGETjson(self, query=""):
        """Make a GET request and return the JSON response"""
        try:
            full_url = self.url + query
            # print(f"DEBUG: Making GET request to: {full_url}")
            
            start_time = time.time()
            response = self.session.get(full_url, timeout=self.timeout)
            elapsed = time.time() - start_time
            # print(f"DEBUG: GET request took {elapsed:.2f} seconds")
            
            # Check status code
            if response.status_code != 200:
                # print(f"DEBUG: GET response status: {response.status_code}")
                return {}
                
            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                # print(f"DEBUG: Error decoding JSON: {str(e)}")
                return {}
                
        except requests.exceptions.Timeout:
            # print(f"DEBUG: Connection timed out after {self.timeout} seconds")
            return {}
        except requests.exceptions.RequestException as e:
            # print(f"DEBUG: Error in REST GET: {str(e)}")
            return {}
        except Exception as e:
            # print(f"DEBUG: Unexpected error in REST GET: {str(e)}")
            return {}
    
    def restPUTjson(self, json_data):
        """Make a PUT request with JSON data"""
        try:
            # print(f"DEBUG: Making PUT/POST request to: {self.url}")
            # print(f"DEBUG: Request payload: {json_data}")
            
            start_time = time.time()
            response = self.session.post(
                self.url,
                json=json_data,
                headers={'Content-Type': 'application/json; charset=UTF-8'},
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            # print(f"DEBUG: PUT/POST request took {elapsed:.2f} seconds")
            
            if response.status_code != 200:
                # print(f"DEBUG: PUT/POST response status: {response.status_code}")
                return {}
                
            try:
                return response.json()
            except json.JSONDecodeError:
                return {}
                
        except requests.exceptions.Timeout:
            # print(f"DEBUG: Connection timed out after {self.timeout} seconds")
            return {}
        except requests.exceptions.RequestException as e:
            # print(f"DEBUG: Error in REST PUT: {str(e)}")
            return {}
        except Exception as e:
            # print(f"DEBUG: Unexpected error in REST PUT: {str(e)}")
            return {}
