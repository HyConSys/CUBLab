import time
import rospy
from ctrl_pkg.msg import ServoCtrlMsg


pub_manual_drive = rospy.Publisher('manual_drive', ServoCtrlMsg, queue_size=10)
rospy.init_node('deepracer_lanekeeper', anonymous=False)

print('left max + speed')
msg = ServoCtrlMsg()
msg.angle    = 0.9
msg.throttle = 0.9
pub_manual_drive.publish(msg)
time.sleep(10)
print('stop')
msg = ServoCtrlMsg()
msg.angle    = 0
msg.throttle = 0
pub_manual_drive.publish(msg)
print('done')