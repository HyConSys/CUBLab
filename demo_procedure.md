
# DeepRacer Demo Procedure  
**LAST UPDATED: May 11, 2025**  

---

## Jump to Section

- [Quick Reference](#quick-reference)
- [Links](#links)
- [DeepRacer Demo - Procedure](#deepracer-demo---procedure)
- [Pre-Procedure Notes](#pre-procedure-notes)
- [Main Procedure](#main-procedure)
- [Other Procedures](#other-procedures)
- [DeepRacer Demo - Troubleshoot](#deepracer-demo---troubleshoot)
- [Ventuz - Multi-Projector Setup](#ventuz---multi-projector-setup)
- [Controller Graphics Card - HP Z8 G4 Workstation](#controller-graphics-card---hp-z8-g4-workstation)

---

## Quick Reference

**Media Server:**  
`192.168.1.194:12345/OptiTrackRestServer`

**pFaces Server:**  
`192.168.1.144:12345/pFaces/REST/dictionary/DeepRacer1`

**pFaces Command:**  
```ps
D:/Workspace/pFaces-SymbolicControl/ex_gb_fp/deepracer_rt/run_d_1_2_fast.bat
```

---

## Links

- Google doc: DeepRacer Demo Procedure  
- Other Github Resources:  
  - https://github.com/HyConSys/CUBLab  
  - https://github.com/HyConSys/deepracer-utils  

---

## DeepRacer Demo - Procedure

### Pre-Procedure Notes

1. **DeepRacer Power-Up**  
   - Charge both robot batteries: one for the drivetrain and one for the compute board.  
   - If battery is low, the robot may ignore compute server commands.

2. **Compute Server IP Configuration**  
   - On the compute and media servers, run:  
     ```ps
     ipconfig
     ```  
   - Edit these robot files:  
     - `closedloop_rt.py`  
     - `closedloop_online.py`  
   - Example configuration:  
     ```python
     LOCALIZATION_SERVER_IPPORT = "192.168.1.194:12345"
     COMPUTE_SERVER_IPPORT = "192.168.1.147:12345"
     ```

3. **SSH into Robot**  
   ```bash
   ssh deepracer@192.168.1.70
   ```  
   Password: `deepracer1234`  
   Retry if connection times out.

4. **Before Running closedloop_rt.py**  
   - Place one obstacle and one target on the mat.

5. **Log Files**  
   - Stored in: `deepracer-utils/examples/sym_control/`  
   - Format: `%d%m%Y%H%M`

6. **Troubleshooting**  
   - [HyConSys GitHub](https://github.com/HyConSys)

---

### Main Procedure

1. **Power & Projectors**  
   - Do **not** hit the reset button on the robot.  
   - Connect both batteries.  
   - Turn robot on (press power button up to 3 times).  
   - Turn on all 4 projectors using the remote.

2. **Media Server GUI**  
   ```ps
   cd D:/Workspace/ArenaManager
   python AutoDeploy.py
   ```  
   - This launches the GUI to start Ventuz, Motive, and the localization server.  
   - Click `Initialize Environment` to project grid.

3. **Controller (on Compute Server)**  
   - Run the shortcut or manually execute:  
     ```ps
     D:/Workspace/pFaces-SymbolicControl/ex_gb_fp/deepracer_rt/run_d_1_2_fast.bat
     ```

4. **DeepRacer 1**  
   ```bash
   ssh deepracer@192.168.1.70
   ```  
   ```bash
   source /opt/aws/deepracer/setup.sh
   python ~/deepracer-utils/put_best_cal.py
   cd deepracer-utils/examples/sym_control
   python closedloop_rt.py
   ```

---

## Other Procedures

### DeepRacer Obstacle

```bash
ssh root@192.168.1.110
```  
```bash
source /opt/ros/foxy/setup.sh
source /root/deepracer_ws/aws-deepracer-servo-pkg/install/setup.sh
cd deepracer-utils/tools
python3 ManualControlServer.py
```  
Open new terminal:  
```ps
python C:/Users/CUBLab/Desktop/KeyboardControl.py
```

### DeepRacer1 with Auto Button

1. SSH into robot
2. Place targets/obstacles via Arena Manager GUI
3. Enable log (if needed)
4. Click `connect and go to target`
5. After run, click `transfer and delete files`  
   Saved to: `C:/Users/CUBLab/Desktop/deepracer-logs`

---

## DeepRacer Demo - Troubleshoot

### Basic Issues

- **No beeping when powering on:** battery may be locked. Use jumper cable.
- **Grid not showing after init:** reboot and retry steps.
- **License error:** email Mahmoud and replace all license files.
- **SSH timeout (step 1):** try up to 15 times, then reboot and check batteries.
- **Robot doesn’t move (step 5):**
  - Batteries charged?
  - Correct server IP?
- **Inspect packets:**  
  ```bash
  sudo tcpdump -w FileName.pcap
  ```  
  Open with Wireshark.

- **Check execution flow:** add print statements, wrap functions in try-except.

Example:
```python
def getMode(self):
    return self.rest_client.restGETjson()["mode"]
```

- **Obstacle moves without command:** reboot all systems.
- **Flush logs:**  
  ```bash
  sudo rm -r /home/deepracer/.ros/log/*
  [optional] sudo rm -r /var/log/*
  ```

---

## Ventuz - Multi-Projector Setup

**Problem:** Only one display appears in Ventuz despite multiple projectors working outside it.

**Fix (Ventuz 6.9):**  
1. Clean AMD drivers with AMD Cleanup Utility  
2. Reinstall latest AMD drivers  
3. Setup Eyefinity in AMD software  
4. Launch Ventuz — merged display should appear

**Ventuz 7+ Notes:**  
- Windows 10: works without spanning  
- Windows 11: may require Eyefinity/Mosaic for sync

---

## Controller Graphics Card - HP Z8 G4 Workstation

### System Info:
- Model: HP Z8 G4 RCTO Base Model
- Serial: MXL12446V8

### Problem 1: No Display Signal
**Fix:**  
- Remove Thunderbolt 3 PCIe card  
- Reconnect NVIDIA GPU  
- Update BIOS to v2.94 Rev A

### Problem 2: RAM Error 3.2
**Fix:**  
- Disconnect power and devices  
- Press yellow CMOS reset switch (5–8 sec)  
- Boot with minimal config: 1 RAM stick  
- Reconnect and test POST

---

## closedloop_rt.py - Troubleshoot Summary & Next Steps

### Issues in Original Controller

- **Missing Theta Normalization**  
- **Incomplete Hyperrectangle Format**
- **Poor Error Handling**
- **No Timeout Handling**

### Improved Controllers

1. **closedloop_rt_robust.py**  
   - Theta normalization with warning  
   - Better error messages and logs

2. **robust_controller_py27.py**  
   - Fixed formatting  
   - Improved connections

3. **robust_controller_recalibrated.py**  
   - Mapped full theta range

4. **hybrid_controller.py**  
   - 3-min initial / 3-sec recurring timeouts  
   - Data caching and graceful fallback

---

## Latest Development: Server Connection Issue

### Observations
- **Simple test works instantly**
- **Full controller has 2–3 min delay**

### Suspected Causes
- Connection reuse problems  
- Python 2.7 networking limitations  
- Complex error handling adds latency

### Diagnostics
- **Seven tests** from direct HTTP to full controller sequence
- Check each layer for delay origin

### Recommendations
- Install Python 3.8 if Python 2.7 is root cause

