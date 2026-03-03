#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Sensor class for the arudino_python package
    Updated for Python3 / ROS Noetic
"""

import rospy
from sensor_msgs.msg import Range
from ros_arduino_msgs.msg import Analog, AnalogFloat, Digital, SensorState

LOW = 0
HIGH = 1

INPUT = 0
OUTPUT = 1

class MessageType:
    ANALOG = 0
    DIGITAL = 1
    RANGE = 2
    FLOAT = 3
    INT = 4
    BOOL = 5


class Sensor:
    def __init__(self, controller, name, pin, rate, frame_id,
                 direction="input", **kwargs):

        self.controller = controller
        self.name = name
        self.pin = pin
        self.rate = rate
        self.direction = direction

        self.frame_id = frame_id
        self.value = None

        self.t_delta = rospy.Duration(1.0 / self.rate)
        self.t_next = rospy.Time.now() + self.t_delta

    def poll(self):
        now = rospy.Time.now()
        if now > self.t_next:
            # Read or write
            if self.direction == "input":
                try:
                    self.value = self.read_value()
                except Exception:
                    return
            else:
                try:
                    self.ack = self.write_value()
                except Exception:
                    return

            # Fill message
            if self.message_type == MessageType.RANGE:
                self.msg.range = self.value
            else:
                self.msg.value = self.value

            # Timestamp + publish
            self.msg.header.stamp = rospy.Time.now()
            self.pub.publish(self.msg)

            self.t_next = now + self.t_delta


# ----------------------------------------------------------------------
# Analog sensors
# ----------------------------------------------------------------------
class AnalogSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super(AnalogSensor, self).__init__(*args, **kwargs)

        self.message_type = MessageType.ANALOG
        self.msg = Analog()
        self.msg.header.frame_id = self.frame_id

        self.pub = rospy.Publisher("~sensor/" + self.name, Analog, queue_size=5)

        # Set pin mode
        if self.direction == "output":
            self.controller.pin_mode(self.pin, OUTPUT)
        else:
            self.controller.pin_mode(self.pin, INPUT)

        self.value = LOW

    def read_value(self):
        return self.controller.analog_read(self.pin)

    def write_value(self):
        return self.controller.analog_write(self.pin, self.value)


class AnalogFloatSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super(AnalogFloatSensor, self).__init__(*args, **kwargs)

        self.message_type = MessageType.ANALOG
        self.msg = AnalogFloat()
        self.msg.header.frame_id = self.frame_id

        self.pub = rospy.Publisher("~sensor/" + self.name, AnalogFloat, queue_size=5)

        if self.direction == "output":
            self.controller.pin_mode(self.pin, OUTPUT)
        else:
            self.controller.pin_mode(self.pin, INPUT)

        self.value = LOW

    def read_value(self):
        return self.controller.analog_read(self.pin)

    def write_value(self):
        return self.controller.analog_write(self.pin, self.value)


# ----------------------------------------------------------------------
# Digital Sensors
# ----------------------------------------------------------------------
class DigitalSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super(DigitalSensor, self).__init__(*args, **kwargs)

        self.message_type = MessageType.BOOL
        self.msg = Digital()
        self.msg.header.frame_id = self.frame_id
        self.pub = rospy.Publisher("~sensor/" + self.name, Digital, queue_size=5)

        if self.direction == "output":
            self.controller.pin_mode(self.pin, OUTPUT)
        else:
            self.controller.pin_mode(self.pin, INPUT)

        self.value = LOW

    def read_value(self):
        return self.controller.digital_read(self.pin)

    def write_value(self):
        # Toggle output
        self.value = not self.value
        return self.controller.digital_write(self.pin, self.value)


# ----------------------------------------------------------------------
# Range Sensors
# ----------------------------------------------------------------------
class RangeSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super(RangeSensor, self).__init__(*args, **kwargs)

        self.message_type = MessageType.RANGE
        self.msg = Range()
        self.msg.header.frame_id = self.frame_id

        self.pub = rospy.Publisher("~sensor/" + self.name, Range, queue_size=5)


class SonarSensor(RangeSensor):
    def __init__(self, *args, **kwargs):
        super(SonarSensor, self).__init__(*args, **kwargs)
        self.msg.radiation_type = Range.ULTRASOUND


class IRSensor(RangeSensor):
    def __init__(self, *args, **kwargs):
        super(IRSensor, self).__init__(*args, **kwargs)
        self.msg.radiation_type = Range.INFRARED


class Ping(SonarSensor):
    def __init__(self, *args, **kwargs):
        super(Ping, self).__init__(*args, **kwargs)
        self.msg.field_of_view = 0.785398163
        self.msg.min_range = 0.02
        self.msg.max_range = 3.0

    def read_value(self):
        # Arduino returns cm
        cm = self.controller.ping(self.pin)
        return cm / 100.0  # convert to meters


class GP2D12(IRSensor):
    def __init__(self, *args, **kwargs):
        super(GP2D12, self).__init__(*args, **kwargs)

        self.msg.field_of_view = 0.001
        self.msg.min_range = 0.10
        self.msg.max_range = 0.80

    def read_value(self):
        value = self.controller.analog_read(self.pin)

        if value <= 3.0:
            return self.msg.max_range

        try:
            distance = (6787.0 / (float(value) - 3.0)) - 4.0
        except Exception:
            return self.msg.max_range

        distance /= 100.0  # cm → m

        if distance > self.msg.max_range:
            distance = self.msg.max_range
        if distance < self.msg.min_range:
            distance = self.msg.max_range

        return distance


class PololuMotorCurrent(AnalogFloatSensor):
    def read_value(self):
        # mA = analog * 34
        milliamps = self.controller.analog_read(self.pin) * 34
        return milliamps / 1000.0


class PhidgetsVoltage(AnalogFloatSensor):
    def read_value(self):
        return 0.06 * (self.controller.analog_read(self.pin) - 500.0)


class PhidgetsCurrent(AnalogFloatSensor):
    def read_value(self):
        return 0.05 * (self.controller.analog_read(self.pin) - 500.0)


class MaxEZ1Sensor(SonarSensor):
    def __init__(self, *args, **kwargs):
        super(MaxEZ1Sensor, self).__init__(*args, **kwargs)

        self.trigger_pin = kwargs['trigger_pin']
        self.output_pin = kwargs['output_pin']

        self.msg.field_of_view = 0.785398163
        self.msg.min_range = 0.02
        self.msg.max_range = 3.0

    def read_value(self):
        return self.controller.get_MaxEZ1(self.trigger_pin, self.output_pin)
