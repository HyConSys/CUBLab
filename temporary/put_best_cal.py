import rospy
#import rospack
from servo_pkg.srv import ServoCalSrv, GetCalSrv


# Set to best min/max calibration for steering
SERVO_MAX = 1790000
SERVO_MID = 1500000
SERVO_MIN = 1080000

# Set to best min/max calibration for speed
MOTOR_MAX = 1603500
MOTOR_MID = 1446000
MOTOR_MIN = 1311000


def main():
    rospy.wait_for_service('servo_cal')
    servo_cal = rospy.ServiceProxy('servo_cal', ServoCalSrv)
    print("Setting the AWS DR calibration ...")
    try:
        servo_cal(0, SERVO_MAX, SERVO_MID, SERVO_MIN, 1)
        servo_cal(1, MOTOR_MAX, MOTOR_MID, MOTOR_MIN, -1)
    except rospy.ServiceException as exc:
        print("Setting calibration failed: " + str(exc))
    print("Setting calibration done!")


if __name__ == "__main__":
    main()