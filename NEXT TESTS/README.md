# DeepRacer Connection Diagnostic Tests

This directory contains a series of diagnostic test scripts designed to pinpoint exactly where and why the connection delay occurs in the DeepRacer controller. Each test builds incrementally on the previous one to isolate the specific component or interaction causing the 3-minute delay.

## Test Scripts Overview

### 1. Basic Connection Test (`test1_basic_connection.py`)
- Tests the most basic direct HTTP connection to the OptiTrack server
- Uses `httplib2` with minimal code, similar to the working `synth_and_test.py`
- Measures connection time and displays basic response data

### 2. RESTApiClient Test (`test2_rest_client.py`)
- Tests if using the `RESTApiClient` class introduces any delay
- Isolates whether the abstraction layer adds overhead
- Compares connection time with the basic HTTP connection

### 3. LocalizationServerInterface Test (`test3_localization_interface.py`)
- Tests if the `LocalizationServerInterface` class adds delay
- Measures time for both getting rigid body state and hyperrectangles
- Identifies if the higher-level interface is causing issues

### 4. pFaces Connection Test (`test4_pfaces_connection.py`)
- Tests the connection to the pFaces server specifically
- Isolates whether the delay is with OptiTrack or pFaces
- Makes a simple dummy request to measure connection time

### 5. Synthesize Controller Test (`test5_synthesize_controller.py`)
- Tests the controller synthesis step specifically
- Measures time for creating a controller, synthesizing, and getting controls
- Uses the pattern from the working `synth_and_test.py` example

### 6. Connection Reuse Test (`test6_connection_reuse.py`)
- Tests if reusing the same HTTP connection causes delays
- Makes multiple consecutive requests with the same connection
- Compares timing between first, second, and third requests

### 7. Full Controller Sequence Test (`test7_full_controller_sequence.py`)
- Tests the full controller sequence with detailed timing for each step
- Breaks down the process into 10 discrete steps with timing for each
- Identifies exactly which step in the sequence is causing the delay

## How to Use

1. Update the server URLs in each script to match your environment
2. Run each test script individually:
   ```
   python test1_basic_connection.py
   ```
3. Compare the timing results to identify where the delay occurs
4. Focus on the specific component or interaction causing the delay

## Expected Results

These tests should help pinpoint one of the following issues:

1. **Connection Reuse**: If test6 shows increasing delays with each reused connection
2. **Network Stack**: If test1 is fast but test2 is slow (RESTApiClient implementation)
3. **Error Handling**: If specific steps in test7 add significant overhead
4. **Python 2.7 Limitations**: If all tests show consistent delays that don't appear in Python 3.8

## Next Steps

After identifying the specific cause of the delay:

1. Implement a targeted fix for that specific component
2. Consider migrating to Python 3.8 for improved networking capabilities
3. Use the hybrid approach with longer initial timeouts and data caching
