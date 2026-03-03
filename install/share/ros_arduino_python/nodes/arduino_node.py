#!/usr/bin/env python3
"""
    这是上位机端主入口总程序，arduino_driver.py、base_controller.py的类都是在
    这里调用的。在这里首先获取参数服务其中订阅的参数，调用类连接arduino、订阅cmd_vel
    消息，以及发送odom。另外，他还封装了一些直接操作arduino的服务端，可以直接调用（设
    置电平等）。
"""

import rospy
from ros_arduino_python.arduino_driver import Arduino
from ros_arduino_python.arduino_sensors import *
from ros_arduino_python.base_controller import BaseController
from ros_arduino_msgs.srv import *
from geometry_msgs.msg import Twist
import os
import time
import threading
from serial.serialutil import SerialException


class ArduinoROS:
    # 该函数是初始化、也是主循环函数
    def __init__(self):
        # ==========1.初始化（获取yaml等）
        rospy.init_node('arduino', log_level=rospy.INFO)

        # 获取launch文件最终生效的节点名
        self.name = rospy.get_name()

        # 关闭节点函数
        rospy.on_shutdown(self.shutdown)

        # 获取参数（yaml）
        self.port = rospy.get_param("~port", "/dev/ttyACM0")
        self.baud = int(rospy.get_param("~baud", 57600))
        self.timeout = rospy.get_param("~timeout", 0.5)
        self.base_frame = rospy.get_param("~base_frame", 'base_link')
        self.motors_reversed = rospy.get_param("~motors_reversed", False)   # 电机反方向

        # 设置主循环频率
        self.rate = int(rospy.get_param("~rate", 50))
        r = rospy.Rate(self.rate)

        # 合并并发布sensor_state（传感器数据）的频率（低频）
        self.sensorstate_rate = int(rospy.get_param("~sensorstate_rate", 10))

        # 是否启动底盘控制器
        self.use_base_controller = rospy.get_param("~use_base_controller", False)
        
        # 设置传感器数据发布时间
        now = rospy.Time.now()  # 当前时间戳
        self.t_delta_sensors = rospy.Duration(1.0 / self.sensorstate_rate)  # 发布sensor_state的时间，每隔该时间发布一次
        self.t_next_sensors = now + self.t_delta_sensors                    # 下一次发布的时间

        self.cmd_vel = Twist()

        # 控制话题创建
        self.cmd_vel_pub = rospy.Publisher('cmd_vel', Twist, queue_size=5)

        # 合并后的传感器状态消息
        self.sensorStatePub = rospy.Publisher('~sensor_state', SensorState, queue_size=5)

        # 订阅这些服务，分别调用arduino相关服务（就是服务控制小车的）
        rospy.Service('~servo_write', ServoWrite, self.ServoWriteHandler)       # 写舵机角度/位置
        rospy.Service('~servo_read', ServoRead, self.ServoReadHandler)          # 读取舵机当前值
        rospy.Service('~digital_set_direction', DigitalSetDirection, self.DigitalSetDirectionHandler) # 设置数字口输入/输出模式
        rospy.Service('~digital_write', DigitalWrite, self.DigitalWriteHandler) # 写数字口电平（HIGH/LOW）
        rospy.Service('~digital_read', DigitalRead, self.DigitalReadHandler)    # 读数字口电平
        rospy.Service('~analog_write', AnalogWrite, self.AnalogWriteHandler)    # 写模拟输出（PWM）
        rospy.Service('~analog_read', AnalogRead, self.AnalogReadHandler)       # 读取模拟输入（ADC）

        # 创建并链接arduino
        self.controller = Arduino(self.port, self.baud, self.timeout, self.motors_reversed)

        # 打开串口
        self.controller.connect()

        rospy.loginfo(f"Connected to Arduino on port {self.port} at {self.baud} baud")

        # 创建互斥锁
        mutex = threading.Lock()

        # 传感器列表
        self.mySensors = []

        sensor_params = rospy.get_param("~sensors", {})

        # ==========2.根据参数动态创建传感器对象并获取传感器参数
        for name, params in sensor_params.items():

            # Default direction = input
            params.setdefault('direction', 'input')

            sensor = None
            if params['type'] == "Ping":
                sensor = Ping(self.controller, name, params['pin'], params['rate'], self.base_frame)
            elif params['type'] == "GP2D12":
                sensor = GP2D12(self.controller, name, params['pin'], params['rate'], self.base_frame)
            elif params['type'] == 'Digital':
                sensor = DigitalSensor(self.controller, name, params['pin'], params['rate'], self.base_frame, direction=params['direction'])
            elif params['type'] == 'Analog':
                sensor = AnalogSensor(self.controller, name, params['pin'], params['rate'], self.base_frame, direction=params['direction'])
            elif params['type'] == 'PololuMotorCurrent':
                sensor = PololuMotorCurrent(self.controller, name, params['pin'], params['rate'], self.base_frame)
            elif params['type'] == 'PhidgetsVoltage':
                sensor = PhidgetsVoltage(self.controller, name, params['pin'], params['rate'], self.base_frame)
            elif params['type'] == 'PhidgetsCurrent':
                sensor = PhidgetsCurrent(self.controller, name, params['pin'], params['rate'], self.base_frame)

            if sensor is not None:
                self.mySensors.append(sensor)
                rospy.loginfo(f"{name} {params} published on topic {rospy.get_name()}/sensor/{name}")
            else:
                rospy.logerr(f"Sensor type {params['type']} not recognized.")

        # ==========3、初始化底盘控制器（self.name为这个节点名）
        if self.use_base_controller:
            self.myBaseController = BaseController(self.controller, self.base_frame, self.name + "_base_controller")

        # ==========4、主循环
        while not rospy.is_shutdown():
            # 根据迭代列表，操作多个传感器
            for sensor in self.mySensors:
                # 使用互斥锁（防止多线程同时操作串口）
                with mutex:
                    sensor.poll()

            # 发布odom数据和订阅‘cmd_vel’消息速度
            if self.use_base_controller:
                with mutex:
                    self.myBaseController.poll()

            # 时间判断
            now = rospy.Time.now()
            
            # 发布传感器数据
            if now > self.t_next_sensors:
                # sensor_msgs/SensorState消息类型
                msg = SensorState()
                msg.header.frame_id = self.base_frame
                msg.header.stamp = now

                for s in self.mySensors:
                    msg.name.append(s.name)
                    msg.value.append(s.value)

                try:
                    self.sensorStatePub.publish(msg)
                except Exception:
                    pass

                self.t_next_sensors = now + self.t_delta_sensors

            r.sleep()

    # ==========5.服务回调（具体函数在arduino_driver.py)
    def ServoWriteHandler(self, req):
        self.controller.servo_write(req.id, req.value)
        return ServoWriteResponse()

    def ServoReadHandler(self, req):
        pos = self.controller.servo_read(req.id)
        return ServoReadResponse(pos)

    def DigitalSetDirectionHandler(self, req):
        self.controller.pin_mode(req.pin, req.direction)
        return DigitalSetDirectionResponse()

    def DigitalWriteHandler(self, req):
        self.controller.digital_write(req.pin, req.value)
        return DigitalWriteResponse()

    def DigitalReadHandler(self, req):
        value = self.controller.digital_read(req.pin)
        return DigitalReadResponse(value)

    def AnalogWriteHandler(self, req):
        self.controller.analog_write(req.pin, req.value)
        return AnalogWriteResponse()

    def AnalogReadHandler(self, req):
        value = self.controller.analog_read(req.pin)
        return AnalogReadResponse(value)

    # ==========6.关闭节点函数
    def shutdown(self):
        rospy.loginfo("Shutting down Arduino Node...")

        # 将将小车停止
        try:
            rospy.loginfo("Stopping the robot...")
            self.cmd_vel_pub.publish(Twist())
            rospy.sleep(2)
        except Exception:
            pass

        # 关闭arduino服务串口
        try:
            self.controller.close()
        except Exception:
            pass
        finally:
            rospy.loginfo("Serial port closed.")
            os._exit(0)


if __name__ == '__main__':
    try:
        ArduinoROS()
    except SerialException:
        rospy.logerr("Serial exception trying to open port.")
        os._exit(0)
