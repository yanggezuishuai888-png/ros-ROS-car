#!/usr/bin/env python3

import rospy
from ros_arduino_python.arduino_driver import Arduino
from ros_arduino_python.arduino_sensors import *
from ros_arduino_msgs.srv import *
from ros_arduino_python.base_controller import BaseController
from geometry_msgs.msg import Twist
import os
import time
import threading
from serial.serialutil import SerialException


class ArduinoROS:
    def __init__(self):
        rospy.init_node('arduino', log_level=rospy.INFO)

        # Get the actual node name in case it is set in the launch file
        self.name = rospy.get_name()

        # Cleanup when terminating the node
        rospy.on_shutdown(self.shutdown)

        self.port = rospy.get_param("~port", "/dev/ttyACM0")
        self.baud = int(rospy.get_param("~baud", 57600))
        self.timeout = rospy.get_param("~timeout", 0.5)
        self.base_frame = rospy.get_param("~base_frame", 'base_link')
        self.motors_reversed = rospy.get_param("~motors_reversed", False)

        # Overall loop rate: should be faster than the fastest sensor rate
        self.rate = int(rospy.get_param("~rate", 50))
        r = rospy.Rate(self.rate)

        # Rate at which summary SensorState message is published
        self.sensorstate_rate = int(rospy.get_param("~sensorstate_rate", 10))

        self.use_base_controller = rospy.get_param("~use_base_controller", False)

        now = rospy.Time.now()
        self.t_delta_sensors = rospy.Duration(1.0 / self.sensorstate_rate)
        self.t_next_sensors = now + self.t_delta_sensors

        # Initialize a Twist message
        self.cmd_vel = Twist()

        # cmd_vel publisher so we can stop robot on shutdown
        self.cmd_vel_pub = rospy.Publisher('cmd_vel', Twist, queue_size=5)

        # Publish all sensor values on a single consolidated topic
        self.sensorStatePub = rospy.Publisher('~sensor_state', SensorState, queue_size=5)

        # ROS Services
        rospy.Service('~servo_write', ServoWrite, self.ServoWriteHandler)
        rospy.Service('~servo_read', ServoRead, self.ServoReadHandler)
        rospy.Service('~digital_set_direction', DigitalSetDirection, self.DigitalSetDirectionHandler)
        rospy.Service('~digital_write', DigitalWrite, self.DigitalWriteHandler)
        rospy.Service('~digital_read', DigitalRead, self.DigitalReadHandler)
        rospy.Service('~analog_write', AnalogWrite, self.AnalogWriteHandler)
        rospy.Service('~analog_read', AnalogRead, self.AnalogReadHandler)

        # Initialize Arduino controller
        self.controller = Arduino(self.port, self.baud, self.timeout, self.motors_reversed)

        # Connect
        self.controller.connect()

        rospy.loginfo(f"Connected to Arduino on port {self.port} at {self.baud} baud")

        # Thread lock (Python3 uses threading)
        mutex = threading.Lock()

        # Initialize sensors
        self.mySensors = []

        sensor_params = rospy.get_param("~sensors", {})

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

        # Initialize the base controller
        if self.use_base_controller:
            self.myBaseController = BaseController(self.controller, self.base_frame, self.name + "_base_controller")

        # Main loop
        while not rospy.is_shutdown():
            for sensor in self.mySensors:
                with mutex:
                    sensor.poll()

            if self.use_base_controller:
                with mutex:
                    self.myBaseController.poll()

            # Publish aggregated sensor values
            now = rospy.Time.now()

            if now > self.t_next_sensors:
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

    # -------- Service callbacks --------
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

    # -------- Shutdown --------
    def shutdown(self):
        rospy.loginfo("Shutting down Arduino Node...")

        # Stop the robot
        try:
            rospy.loginfo("Stopping the robot...")
            self.cmd_vel_pub.publish(Twist())
            rospy.sleep(2)
        except Exception:
            pass

        # Close serial port
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
