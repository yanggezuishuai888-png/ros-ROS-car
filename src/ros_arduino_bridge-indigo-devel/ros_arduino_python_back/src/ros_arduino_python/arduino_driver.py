#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    这个主要是arduino交互程序，arduino握手、串口发送、
    串口读取的封装，即在固件中手动输入的命令这里全部封装
    成了函数，主要给arduino_node调用
"""
import threading
from math import pi as PI, degrees, radians
import os
import time
import sys
import traceback
from serial.serialutil import SerialException
from serial import Serial

# 舵机角度范围
SERVO_MAX = 180
SERVO_MIN = 0

class Arduino:
    ''' Configuration Parameters '''
    N_ANALOG_PORTS = 6
    N_DIGITAL_PORTS = 12

    # ----------------------------------------------------------------------
    # 1.串口即参数初始化
    # ----------------------------------------------------------------------
    def __init__(self, port="/dev/ttyUSB0", baudrate=57600, timeout=0.5, motors_reversed=False):

        self.PID_RATE = 30                      # Arduino 那边 PID 控制循环频率（Hz）
        self.PID_INTERVAL = 1000 / 30           # 每次 PID 间隔的毫秒数

        self.port_name = port                   # 串口名，比如 /dev/ttyACM0
        self.baudrate = baudrate        
        self.timeout = timeout                  # 串口读写超时时间
        self.encoder_count = 0
        self.writeTimeout = timeout             # 字符级超时时间，用在 recv() 里避免死等
        self.interCharTimeout = timeout / 30.0
        self.motors_reversed = motors_reversed  # 如果电机接线反了，逻辑上把左右速度取反即可

        # 线程锁
        self.mutex = threading.Lock()

        # analog / digital 的缓存
        self.analog_sensor_cache = [None] * self.N_ANALOG_PORTS
        self.digital_sensor_cache = [None] * self.N_DIGITAL_PORTS

        self.port = None  # Serial对象
    # ----------------------------------------------------------------------
    # 2.检测串口能否正常通信（初始化连接，即握手）
    # ----------------------------------------------------------------------
    def connect(self):
        try:
            print(f"尝试连接串口 {self.port_name} ...")
            # 打开串口
            self.port = Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                timeout=self.timeout,
                writeTimeout=self.writeTimeout
            )

            # 等待arduino启动
            time.sleep(1)
            # 发一个 b 命令
            test = self.get_baud()
            # 看 Arduino 回应的波特率是不是和期望值一致
            if test != self.baudrate:
                time.sleep(1)
                # 多试一次
                test = self.get_baud()
                if test != self.baudrate:
                    raise SerialException

            print(f"Connected at {self.baudrate}")
            print("Arduino is ready.")

        except SerialException:
            print("Serial Exception:")
            print(sys.exc_info())
            traceback.print_exc(file=sys.stdout)
            print("Cannot connect to Arduino!")
            os._exit(1)

    def open(self):
        if self.port:
            self.port.open()

    def close(self):
        if self.port:
            self.port.close()

    # ----------------------------------------------------------------------
    # 3.各种读取函数
    # ----------------------------------------------------------------------
    # 向arduino发送命令函数（拼接一个回车符）。这里暂未调用
    def send(self, cmd):
        self.port.write((cmd + '\r').encode('ascii'))

    # 从串口中读取命令
    def recv(self, timeout=0.5):
        timeout = min(timeout, self.timeout)    # 设置读取超时时间
        value = b''
        attempts = 0                            # 统计读不到数据次数

        while True:
            c = self.port.read(1)               # 逐个读取
            # 超时前仍旧没读到数据就返回空字节（b'')
            if c == b'':
                attempts += 1
                if attempts * self.interCharTimeout > timeout:
                    return None
                continue
            # 否则将结果加到value
            value += c
            if c == b'\r':
                break
        # 二进制转成字符串（ASCI）并去掉'\r'
        return value.decode('ascii').strip('\r')

    # 判断是否读取成功
    def recv_ack(self):
        return self.recv(self.timeout) == 'OK'

    # 读取一个整数
    def recv_int(self):
        val = self.recv(self.timeout)
        try:
            return int(val)
        except:
            return None
    # 读取一组整数
    def recv_array(self):
        """Returns list of ints."""
        try:
            raw = self.recv(self.timeout * self.N_ANALOG_PORTS)
            if raw is None:
                return []
                # .split（）表示按照空格划分
            return list(map(int, raw.split()))
        except:
            return []

    # ----------------------------------------------------------------------
    # 4.各种发命令函数
    # ----------------------------------------------------------------------
    # 发送后返回一个整数
    def execute(self, cmd):
        # 互斥锁
        with self.mutex:
            try:
                self.port.reset_input_buffer()
            except:
                pass

            ntries = 1
            attempts = 0
            value = None

            try:
                self.port.write((cmd + '\r').encode('ascii'))
                value = self.recv(self.timeout)

                while attempts < ntries and (value in ['', 'Invalid Command', None]):
                    try:
                        self.port.reset_input_buffer()
                        self.port.write((cmd + '\r').encode('ascii'))
                        value = self.recv(self.timeout)
                    except:
                        print("Exception executing command:", cmd)
                    attempts += 1

            except:
                print("Exception executing command:", cmd)

        try:
            return int(value)
        except:
            return None

    # 发送后返回多个整数
    def execute_array(self, cmd):
        """Return array of ints."""
        with self.mutex:
            try:
                self.port.reset_input_buffer()
            except:
                pass

            ntries = 1
            attempts = 0

            values = []

            try:
                self.port.write((cmd + '\r').encode('ascii'))
                values = self.recv_array()

                while attempts < ntries and (values in ['', 'Invalid Command', [], None]):
                    try:
                        self.port.reset_input_buffer()
                        self.port.write((cmd + '\r').encode('ascii'))
                        values = self.recv_array()
                    except:
                        print(f"Exception executing command: {cmd}")
                    attempts += 1

            except:
                print(f"Exception executing command: {cmd}")
                raise SerialException

            if values is None:
                return []

            try:
                return list(map(int, values))
            except:
                return []

    # 发送后仅返回 OK或者其他失败符号（False）
    def execute_ack(self, cmd):
        # 互斥锁（进入with时就上锁）
        with self.mutex:
            try:
                # 清空串口
                self.port.reset_input_buffer()
            except:
                pass
            
            ntries = 1      # 最大尝试次数
            attempts = 0    # 当前已经尝试了多少次 
            ack = None      # 接收字符串

            try:
                # 往串口写命令。 .encode('ascii') - 转ASCLL编码（"m 10 10" - b"m 10 10\r"） 
                self.port.write((cmd + '\r').encode('ascii'))
                # 读串口回应
                ack = self.recv(self.timeout)

                # 重试发送
                while attempts < ntries and (ack in ['', 'Invalid Command', None]):
                    try:
                        self.port.reset_input_buffer()
                        self.port.write((cmd + '\r').encode('ascii'))
                        ack = self.recv(self.timeout)
                    except:
                        print("Exception executing command:", cmd)
                    attempts += 1

            except:
                print("execute_ack exception when executing", cmd)
                print(sys.exc_info())
                return False

        return ack == 'OK'

    # ----------------------------------------------------------------------
    # 5.向arduino发送命令函数（在arduino_node.py中的服务回调中被调用或者直接调用）
    # ----------------------------------------------------------------------
    def update_pid(self, Kp, Kd, Ki, Ko):
        print("Updating PID parameters")
        cmd = f"u {Kp}:{Kd}:{Ki}:{Ko}"
        return self.execute_ack(cmd)

    def get_baud(self):
        try:
            return int(self.execute('b'))
        except:
            return None
    # 获取四个轮子脉冲
    def get_encoder_counts(self):
        values = self.execute_array('e')
        # if len(values) != 2:
        if len(values) != 4:
            print("Encoder count was not 4")
            raise SerialException
        else:
            if self.motors_reversed:
                # values[0], values[1] = -values[0], -values[1]
                values[0], values[1], values[2], values[3] = -values[0], -values[1], -values[2], -values[3]
            return values

    # 对所有电机脉冲清零
    def reset_encoders(self):
        return self.execute_ack('r')

    # m命令 ---- 控制小车动就改这个函数
    # def drive(self, right, left):
    #     # 反转
    #     if self.motors_reversed:
    #         left, right = -left, -right
    #     return self.execute_ack(f"m {right} {left}")
    def drive(self, front_left, front_right, after_left, after_right):
        if self.motors_reversed:
            front_left, front_right, after_left, after_right = -front_left, -front_right, -after_left, -after_right
        return self.execute_ack(f"m {front_left} {front_right} {after_left} {after_right}")
        
    def drive_m_per_s(self, right, left):
        left_rps = float(left) / (self.wheel_diameter * PI)
        right_rps = float(right) / (self.wheel_diameter * PI)

        left_ticks = int(left_rps * self.encoder_resolution * self.PID_INTERVAL * self.gear_reduction)
        right_ticks = int(right_rps * self.encoder_resolution * self.PID_INTERVAL * self.gear_reduction)

        self.drive(right_ticks, left_ticks)

    def stop(self):
        self.drive(0, 0)

    def analog_read(self, pin):
        return self.execute(f"a {pin}")

    def analog_write(self, pin, value):
        return self.execute_ack(f"x {pin} {value}")

    def digital_read(self, pin):
        return self.execute(f"d {pin}")

    def digital_write(self, pin, value):
        return self.execute_ack(f"w {pin} {value}")

    def pin_mode(self, pin, mode):
        return self.execute_ack(f"c {pin} {mode}")

    def servo_write(self, id, pos):
        return self.execute_ack(f"s {id} {min(SERVO_MAX, max(SERVO_MIN, int(degrees(pos))))}")

    def servo_read(self, id):
        return radians(self.execute(f"t {id}"))

    def ping(self, pin):
        return self.execute(f"p {pin}")


# ----------------------------------------------------------------------
# 6.总调用（这边是单独测试的）
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if os.name == "posix":
        portName = "/dev/ttyACM0"
    else:
        portName = "COM43"

    baudRate = 57600

    myArduino = Arduino(port=portName, baudrate=baudRate, timeout=0.5)
    myArduino.connect()

    print("Sleeping for 1 second...")
    time.sleep(1)

    print("Reading on analog port 0:", myArduino.analog_read(0))
    print("Reading on digital port 0:", myArduino.digital_read(0))

    print("Blinking the LED 3 times")
    for i in range(3):
        myArduino.digital_write(13, 1)
        time.sleep(1.0)

    print("Connection test successful.")
    myArduino.stop()
    myArduino.close()
    print("Shutting down Arduino.")
