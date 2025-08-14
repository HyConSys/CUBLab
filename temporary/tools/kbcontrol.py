import sys, termios, tty, os, time
import rospy
from ctrl_pkg.msg import ServoCtrlMsg
from servo_pkg.srv import ServoCalSrv, GetCalSrv

# to store the calibration if needed
SERVO_MAX = 0
SERVO_MID = 0
SERVO_MIN = 0
MOTOR_MAX = 0
MOTOR_MID = 0
MOTOR_MIN = 0

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
 
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def start_cal(pub_manual_drive):
    global SERVO_MAX
    global SERVO_MID
    global SERVO_MIN
    global MOTOR_MAX
    global MOTOR_MID
    global MOTOR_MIN
    print("New calibration process started.")
    print("Reading the current calibration .... ")
    rospy.wait_for_service('servo_cal')
    get_cal = rospy.ServiceProxy('get_cal', GetCalSrv)
    servo_cal = rospy.ServiceProxy('servo_cal', ServoCalSrv)
    resp0 = get_cal(0)
    resp1 = get_cal(1)
    SERVO_MAX = resp0.max
    SERVO_MID = resp0.mid
    SERVO_MIN = resp0.min
    MOTOR_MAX = resp1.max
    MOTOR_MID = resp1.mid
    MOTOR_MIN = resp1.min
    print("Current Calibration:")
    print("Servo [min/mid/max]: " + str(SERVO_MIN) + "/" + str(SERVO_MID) + "/" + str(SERVO_MAX))
    print("Motor [min/mid/max]: " + str(MOTOR_MIN) + "/" + str(MOTOR_MID) + "/" + str(MOTOR_MAX))
    print("Calibrating the servo [Put the car on a flat floor] ... ")
    print("Press [1/2] to [-/+] the servo min.")
    print("Press [3/4] to [-/+] the servo mid.")
    print("Press [5/6] to [-/+] the servo max.")
    print("Press [f] to push the calibration and exit.")
    print("Press [x] to exit without saving.")
    button_delay = 0.1
    inc = 10000
    while True:
        ch = getch()
        if ch == "x":
            break

        elif ch == "f":
            servo_cal(0, SERVO_MAX, SERVO_MID, SERVO_MIN, -1)
            break

        elif ch == "1":
            SERVO_MIN -= inc
            print("SERVO_MIN <= " + str(SERVO_MIN))
            time.sleep(button_delay)

        elif ch == "2":
            SERVO_MIN += inc
            print("SERVO_MIN <= " + str(SERVO_MIN))
            time.sleep(button_delay)

        elif ch == "3":
            SERVO_MID -= inc
            print("SERVO_MID <= " + str(SERVO_MID))
            time.sleep(button_delay)

        elif ch == "4":
            SERVO_MID += inc
            print("SERVO_MID <= " + str(SERVO_MID))
            time.sleep(button_delay)

        elif ch == "5":
            SERVO_MAX -= inc
            print("SERVO_MAX <= " + str(SERVO_MAX))
            time.sleep(button_delay)

        elif ch == "6":
            SERVO_MAX += inc
            print("SERVO_MAX <= " + str(SERVO_MAX))
            time.sleep(button_delay)

def init_publisher():
    pub_manual_drive = rospy.Publisher('manual_drive', ServoCtrlMsg, queue_size=10)
    rospy.init_node('deepracer_lanekeeper', anonymous=False)
    return pub_manual_drive

def stop(pub_manual_drive):
    msg = ServoCtrlMsg()
    msg.angle    = 0.0
    msg.throttle = 0.0
    pub_manual_drive.publish(msg)

# angle and throttle are in [-1,1]
def drive(pub_manual_drive, angle, throttle):
    msg = ServoCtrlMsg()
    msg.angle    = angle
    msg.throttle = throttle
    pub_manual_drive.publish(msg)

def inc(val):
    new_val = val + 0.05
    if new_val > 1.0:
        new_val = 1.0
    return new_val

def dec(val):
    new_val = val - 0.05
    if new_val < -1.0:
        new_val = -1.0
    return new_val

def main():

    current_angle = 0.0
    current_throttle = 0.0

    pub_manual_drive = init_publisher()
    print("AWS Keyboard Controller Ready:")
    print("Use [q,w] for speed, [o, p] for angle,")
    print("[d] for driving, [s] for stopping, and")
    print("[c] for initiating a calibration process.")

    button_delay = 0.1
    while True:
        char = getch()
 
        if (char == "d"):
            print("Driving ... ")
            drive(pub_manual_drive, current_angle, current_throttle)
            time.sleep(button_delay)

        elif (char == "s"):
            print("Stopping ... ")
            stop(pub_manual_drive)
            time.sleep(button_delay)
    
        elif (char == "q"):
            current_throttle = dec(current_throttle)
            print("Speed is: " + str(current_throttle))
            time.sleep(button_delay)
    
        elif (char == "w"):
            current_throttle = inc(current_throttle)
            print("Speed is: " + str(current_throttle))
            time.sleep(button_delay)
    
        elif (char == "o"):
            current_angle = dec(current_angle)
            print("Angle is: " + str(current_angle))
            time.sleep(button_delay)

        elif (char == "p"):
            current_angle = inc(current_angle)
            print("Angle is: " + str(current_angle))
            time.sleep(button_delay)

        elif (char == "c"):
            start_cal(pub_manual_drive)
            print("Calibration done. you are now in main menu.")

        elif (char == "x"):
            print("Exiting ... ")
            break


if __name__ == "__main__":
    main()
