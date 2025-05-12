# DeepRacer Symbolic Controller – README

**synth_and_test** - first test that gets actions from pfaces using hardcoded inputs.

**final_controller.py** - the first working live controller version, run from the Media Server PC.
(**RemoteSymbolicController.py** file was also updated)

Then, **theta issue** was discovered: deepracer theta values changed randomly and `closedloop_rt.py` failed on certain inputs. 

**robust_controller.py** made to clamp theta range.

- `robust_controller_py27.py`: Python 2.7-compatible version used on the DeepRacer.

- `robust_controller_recalibrated_py27.py`: maps ±3.2 to ±1.7.

When tested on deepracer, receive actions after a 2–3 minute delay.

**simple_optitrack_test.py** tests different connection methods:  
- `LocalizationServerInterface`  
- `httplib2` with default timeout (same as `RESTApiClient`)  
- `httplib2` with socket-level timeout

Delay issue is still unresolved.