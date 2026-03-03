#!/usr/bin/env python3
# encoding: utf-8

# public lib
import sys
import math
import random
import threading

from YbImuLib import YbImuSerial

# ros lib
import rospy
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Float32MultiArray


class ybimu_driver:
    def __init__(self):
        rospy.init_node('ybimu_node', anonymous=True)
        self.robot = None
        self.init_topic()

    def init_topic(self):
        port_list = ["/dev/myimu", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"]
        for port in port_list:
            try:
                self.robot = YbImuSerial(port)
                rospy.loginfo("Open Ybimu Port OK:%s" % port)
                break
            except:
                pass
        if self.robot is None:
            rospy.logerr("---------Fail To Open Ybimu Serial------------")
            return
        self.robot.create_receive_threading()

        # create publisher
        self.imuPublisher = rospy.Publisher("imu/data_raw", Imu, queue_size=100)
        # self.magPublisher = rospy.Publisher("imu/mag", MagneticField, queue_size=100)
        self.baroPublisher = rospy.Publisher("baro", Float32MultiArray, queue_size=100)
        self.eulerPublisher = rospy.Publisher("euler", Float32MultiArray, queue_size=100)

        # create timer
        rospy.Timer(rospy.Duration(0.1), self.pub_data)

    # pub data
    def pub_data(self, event):
        if self.robot is None:
            return
        time_stamp = rospy.Time.now()
        imu = Imu()
        imu.orientation_covariance[0] = -1

        # 角速度协方差（rad^2/s^2）表示有多不相信各数值
        imu.angular_velocity_covariance = [
            0.02, 0, 0,
            0, 0.02, 0,
            0, 0, 0.002                      # vyaw方差（0.002一下表示比较相信）
        ]

        # 加速度协方差（(m/s^2)^2）表示有多不相信各数值
        imu.linear_acceleration_covariance = [
            0.2, 0, 0,
            0, 0.2, 0,
            0, 0, 0.2
        ]
        # mag = MagneticField()
        baro = Float32MultiArray()
        euler = Float32MultiArray()

        [ax, ay, az] = self.robot.get_accelerometer_data()
        [gx, gy, gz] = self.robot.get_gyroscope_data()
        # [mx, my, mz] = self.robot.get_magnetometer_data()
        # [q0, q1, q2, q3] = self.robot.get_imu_quaternion_data()
        [height, temperature, pressure, pressure_contrast] = self.robot.get_baro_data()
        [roll, pitch, yaw] = self.robot.get_imu_attitude_data(True)

        # 发布陀螺仪的数据
        G = 9.80665
        imu.header.stamp = time_stamp
        imu.header.frame_id = "imu_link"            # 将角速度从g改成m/s^2
        imu.linear_acceleration.x = ax * G
        imu.linear_acceleration.y = ay * G
        imu.linear_acceleration.z = az * G
        imu.angular_velocity.x = gx * 1.0
        imu.angular_velocity.y = gy * 1.0
        imu.angular_velocity.z = gz * 1.0
        # imu.orientation.w = q0
        # imu.orientation.x = q1
        # imu.orientation.y = q2
        # imu.orientation.z = q3
        imu.orientation.w = 1.0
        imu.orientation.x = 0.0
        imu.orientation.y = 0.0
        imu.orientation.z = 0.0

        # mag.header.stamp = time_stamp
        # mag.header.frame_id = "imu_link"
        # mag.magnetic_field.x = mx * 1.0
        # mag.magnetic_field.y = -my * 1.0
        # mag.magnetic_field.z = mz * 1.0

        baro.data = [height, temperature, pressure, pressure_contrast]
        euler.data = [roll, pitch, yaw]

        self.imuPublisher.publish(imu)
        # self.magPublisher.publish(mag)
        self.baroPublisher.publish(baro)
        self.eulerPublisher.publish(euler)

    def ready(self):
        if self.robot is None:
            return False
        else:
            return True

def main():
    try:
        node = ybimu_driver()
        if not node.ready():
            return
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

if __name__ == "__main__":
    main()
