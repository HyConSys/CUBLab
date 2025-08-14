import rospy
from ctrl_pkg.msg import ServoCtrlMsg

class MotionControls:
    def __init__(self):
        self.pub_manual_drive = None
        self.init_publisher()
        self.stop()

    def init_publisher(self):
        self.pub_manual_drive = rospy.Publisher('manual_drive', ServoCtrlMsg, queue_size=10)
        rospy.init_node('deepracer_lanekeeper', anonymous=False)

    def stop(self):
        msg = ServoCtrlMsg()
        msg.angle    = 0.0
        msg.throttle = 0.0
        self.pub_manual_drive.publish(msg)

    def drive(self, angle, throttle):
        msg = ServoCtrlMsg()
        msg.angle    = angle
        msg.throttle = throttle
        self.pub_manual_drive.publish(msg)

    def __del__(self):
        self.stop()