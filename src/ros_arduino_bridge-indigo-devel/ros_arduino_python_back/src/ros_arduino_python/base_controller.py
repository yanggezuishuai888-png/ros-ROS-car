#!/usr/bin/env python

"""
    这里会读取编码器的数据，订阅’cmd_vel'的数据，读取yaml中PID的数据，
    首先会将PID数据传给Arduino做PID的初始化；然后将读取到的编码器数据
    转化为距离信息，通过odom发送出去；将订阅到的‘cmd_vel’信息转化为速度
    信息，发送给arduino
"""
import roslib; roslib.load_manifest('ros_arduino_python')
import rospy
import os

from math import sin, cos, pi
from geometry_msgs.msg import Quaternion, Twist, Pose
from nav_msgs.msg import Odometry
from tf.broadcaster import TransformBroadcaster

from tf.transformations import euler_from_quaternion
from std_msgs.msg import Float32MultiArray
 
class BaseController:
    # =========1.初始化
    def __init__(self, arduino, base_frame, name="base_controllers"):
        self.euler_pub = rospy.Publisher("odom/euler", Float32MultiArray, queue_size=10)

        self.arduino = arduino          # arduino类对象
        self.name = name                # 节点名称
        self.base_frame = base_frame    # base_link
        self.rate = float(rospy.get_param("~base_controller_rate", 10))
        self.timeout = rospy.get_param("~base_controller_timeout", 1.0)
        self.stopped = False            # 小车停止布尔值（在单独测试时用）

        # 获取PID相关参数
        pid_params = dict()
        pid_params['wheel_diameter'] = rospy.get_param("~wheel_diameter", "")           # 轮子直径（米）
        pid_params['wheel_track'] = rospy.get_param("~wheel_track", "")                 # 轮距（米）
        pid_params['encoder_resolution'] = rospy.get_param("~encoder_resolution", "")   # 编码器每圈脉冲数
        pid_params['gear_reduction'] = rospy.get_param("~gear_reduction", 1.0)          # 减速比
        pid_params['Kp'] = rospy.get_param("~Kp", 20)                                   # PIDO
        pid_params['Kd'] = rospy.get_param("~Kd", 12)
        pid_params['Ki'] = rospy.get_param("~Ki", 0)
        pid_params['Ko'] = rospy.get_param("~Ko", 50)
        
        # 最大加速度  
        self.accel_limit = rospy.get_param('~accel_limit', 0.1)
        # 电机方向                
        self.motors_reversed = rospy.get_param("~motors_reversed", False)   
        
        # 初始化PID
        self.setup_pid(pid_params)
            
        # 每米的编码器脉冲，单位tick/m。
        #   每圈脉冲数 * 减速比 / (轮子直径 * pi) 。 即脉冲数 / 周长（周长 = pi * 直径）
        self.ticks_per_meter = self.encoder_resolution * self.gear_reduction  / (self.wheel_diameter * pi)

        #最大加速度tick值
        self.max_accel = self.accel_limit * self.ticks_per_meter / self.rate
                
        # 编码器计数读取错误次数
        self.bad_encoder_count = 0
        
        # odom发布时间设置
        now = rospy.Time.now()    
        self.then = now # time for determining dx/dy
        self.t_delta = rospy.Duration(1.0 / self.rate)
        self.t_next = now + self.t_delta

        # 速度相关变量        
        self.enc_front_left  = None       # 四个轮编码器tick
        self.enc_front_right = None
        self.enc_after_left  = None
        self.enc_after_right = None
        self.x = 0                        # 机器人实际位置（xy + 偏航角）
        self.y = 0
        self.th = 0                     
        self.v_front_left = 0             # 指定PID周期内要发送的tick
        self.v_front_right = 0
        self.v_after_left = 0
        self.v_after_right = 0

        self.v_des_front_left = 0         # 指定PID周期内的目标tick
        self.v_des_front_right = 0
        self.v_des_after_left = 0
        self.v_des_after_right = 0
        self.last_cmd_vel = now           # 上一次收到/cmd_vel的时间

        # Subscriptions
        rospy.Subscriber("cmd_vel", Twist, self.cmdVelCallback)
        
        # 对所有电机脉冲清零
        self.arduino.reset_encoders()
        
        # odom
        self.odomPub = rospy.Publisher('odom', Odometry, queue_size=5)
        # 创建坐标发布对象
        self.odomBroadcaster = TransformBroadcaster()
        
        rospy.loginfo("Started base controller for a base of " + str(self.wheel_track) + "m wide with " + str(self.encoder_resolution) + " ticks per rev")
        rospy.loginfo("Publishing odometry data at: " + str(self.rate) + " Hz using " + str(self.base_frame) + " as base frame")
    
    # 设置PID。pid_params是一个存着PID等信息的字典
    def setup_pid(self, pid_params):
        missing_params = False
        # 检查PID是否为空
        for param in pid_params:
            if pid_params[param] == "":
                print("*** PID Parameter " + param + " is missing. ***")
                missing_params = True
        
        # 如果pid_params字典中有空值，就直接退出程序
        if missing_params:
            os._exit(1)
                
        self.wheel_diameter = pid_params['wheel_diameter']              # 轮子直径（米）
        self.wheel_track = pid_params['wheel_track']                    # 轮距（米）
        self.encoder_resolution = pid_params['encoder_resolution']      # 编码器每圈脉冲数
        self.gear_reduction = pid_params['gear_reduction']              # 减速比
        self.Kp = pid_params['Kp']                                      # 四个轮子的PIDO
        self.Kd = pid_params['Kd']
        self.Ki = pid_params['Ki']
        self.Ko = pid_params['Ko']
        
        # 先不写PID
        # self.arduino.update_pid(self.Kp, self.Kd, self.Ki, self.Ko)

    # =========2.主循环函数。odom发布、cmd_vel的tick发送都是在这里。该函数也是arduino_node调用的主函数
    def poll(self):
        now = rospy.Time.now()
        # 大于发布时间就操作
        if now > self.t_next:
            try:
                # 读取左右轮脉冲
                enc_front_left, enc_front_right, enc_after_left, enc_after_right = self.arduino.get_encoder_counts()
            except:
                self.bad_encoder_count += 1
                rospy.logerr("Encoder exception count: " + str(self.bad_encoder_count))
                return
            
            # 计算两次poll时间差（self.then是上一次poll执行的时间）
            dt = now - self.then
            self.then = now
            dt = dt.to_sec()    # 将时间转成秒
            
            if self.enc_front_left is None:
                d_front_left  = 0.0
                d_front_right = 0.0
                d_after_left  = 0.0
                d_after_right = 0.0
            else:
                # (本次tick - 上次tick) / 每米tick数 = 轮子位移（米）
                d_front_left  = (enc_front_left  - self.enc_front_left)  / self.ticks_per_meter
                d_front_right = (enc_front_right - self.enc_front_right) / self.ticks_per_meter
                d_after_left  = (enc_after_left  - self.enc_after_left)  / self.ticks_per_meter
                d_after_right = (enc_after_right - self.enc_after_right) / self.ticks_per_meter

            # 更新保存的编码器计数
            self.enc_front_left  = enc_front_left
            self.enc_front_right = enc_front_right
            self.enc_after_left  = enc_after_left
            self.enc_after_right = enc_after_right
            
            # 左右轮位移推到机器人位姿增量
            # 把四个轮子合成“左侧一条履带”和“右侧一条履带”
            dleft  = (d_front_left  + d_after_left)  / 2.0   # 左侧平均位移
            dright = (d_front_right + d_after_right) / 2.0   # 右侧平均位移

            dxy_ave = (dright + dleft) / 2.0                 # 小车线位移
            dth = (dright - dleft) / self.wheel_track        # 小车角度变化（弧度）
            # 防止dt为0
            if dt > 0:
                vxy = dxy_ave / dt                           # 线速度 (m/s)
                vth = dth / dt                               # 角速度 (rad/s)
            else:
                vxy = 0.0
                vth = 0.0

            # 更新机器人在世界坐标系中的位置 (x, y, th)
            if (dxy_ave != 0):
                dx = cos(dth) * dxy_ave
                dy = -sin(dth) * dxy_ave
                self.x += (cos(self.th) * dx - sin(self.th) * dy)
                self.y += (sin(self.th) * dx + cos(self.th) * dy)
    
            if (dth != 0):
                self.th += dth 

            # 组织四元数数据（tf和odom消息共享）
            quaternion = Quaternion()
            quaternion.x = 0.0 
            quaternion.y = 0.0
            quaternion.z = sin(self.th / 2.0)
            quaternion.w = cos(self.th / 2.0)
    
            # 发布一个tf坐标
            # self.odomBroadcaster.sendTransform(
            #     (self.x, self.y, 0),                                        # xyz
            #     (quaternion.x, quaternion.y, quaternion.z, quaternion.w),   # 四元素
            #     rospy.Time.now(),
            #     self.base_frame,                                            # 子级坐标系
            #     "odom"                                                      # 父级坐标系
            #     )
            
            # 组织里程计数据((self.base_frame 相对odom（以初始位置为原点。不动）的位姿))
            odom = Odometry()
            odom.header.frame_id = "odom"                                   
            odom.child_frame_id = self.base_frame                           
            odom.header.stamp = now
            odom.pose.pose.position.x = self.x
            odom.pose.pose.position.y = self.y
            odom.pose.pose.position.z = 0
            odom.pose.pose.orientation = quaternion
            odom.twist.twist.linear.x = vxy
            odom.twist.twist.linear.y = 0
            odom.twist.twist.angular.z = vth

            q = [quaternion.x, quaternion.y, quaternion.z, quaternion.w]
            roll, pitch, yaw = euler_from_quaternion(q)

            msg = Float32MultiArray()
            msg.data = [roll, pitch, yaw]   # rad
            self.euler_pub.publish(msg)

            # 里程计协方差矩阵，表示小车有多不相信。里面每个值都代表一种属性（角速度）的方差
            odom.pose.covariance = [
            0.02, 0,    0, 0, 0, 0,
            0,    0.02, 0, 0, 0, 0,
            0,    0,    1e6,0,0,0,
            0,    0,    0, 1e6,0,0,
            0,    0,    0, 0, 1e6,0,
            0,    0,    0, 0, 0, 0.1        # 里程计的 vyaw 方差
            ]

            odom.twist.covariance = [
            0.02, 0,    0, 0, 0, 0,
            0,    1e6,  0, 0, 0, 0,
            0,    0,    1e6,0,0,0,
            0,    0,    0, 1e6,0,0,
            0,    0,    0, 0, 1e6,0,
            0,    0,    0, 0, 0, 0.5        # odom yaw 方差
            ]

            self.odomPub.publish(odom)
            
            # 没收到 cmd_vel 就逐渐停下来
            if now > (self.last_cmd_vel + rospy.Duration(self.timeout)):

                self.v_des_front_left = 0
                self.v_des_front_right = 0
                self.v_des_after_left = 0
                self.v_des_after_right = 0
            
            # 计算每个轮子要下发给arduino的速度。大就减速、小就加速
            # 4 个轮子速度和目标速度
            wheels = [
                ("front_left", "v_front_left", "v_des_front_left"),
                ("front_right", "v_front_right", "v_des_front_right"),
                ("after_left", "v_after_left", "v_des_after_left"),
                ("after_right", "v_after_right", "v_des_after_right")
            ]

            # 对 4 个轮子进行加速度限制
            for name, v_issue, v_des in wheels:
                # 根据字符串动态获取self属性
                v = getattr(self, v_issue)
                v_des = getattr(self, v_des)

                if v < v_des:
                    v += self.max_accel
                    if v > v_des:
                        v = v_des
                else:
                    v -= self.max_accel
                    if v < v_des:
                        v = v_des
                # 更新要下发的速度
                setattr(self, v_issue, v)   

            # 调用函数，向arduino发送速度
            if not self.stopped:
                # self.arduino.drive(self.v_left, self.v_right)
                self.arduino.drive(self.v_front_left, self.v_front_right, self.v_after_left, self.v_after_right)
            
            # 更新时间
            self.t_next = now + self.t_delta
    
    # 小车停止函数（这里没用上）
    def stop(self):
        self.stopped = True
        self.arduino.drive(0, 0)

    # ========3.cmd_vel订阅，在这里将速度消息转成tick消息
    """
        改四轮思路：
            将两轮的速度赋值到四轮上即可。左轮赋值到左边两轮
    """
    def cmdVelCallback(self, req):
        self.last_cmd_vel = rospy.Time.now()
        
        x = req.linear.x         # m/s
        th = req.angular.z       # rad/s

        # 三种运动模式：原地转、直走、曲线
        if x == 0:               # 原地转
            # ur = ω * L/2
            # right = th * self.wheel_track / 2.0
            right = th * self.wheel_track  * self.gear_reduction / 2.0
            left = -right
        elif th == 0:            # 直线
            left = right = x
        else:                    # 曲线
            # vt = v - (ω * L)/2  
            left = x - th * self.wheel_track  * self.gear_reduction / 2.0
            right = x + th * self.wheel_track  * self.gear_reduction / 2.0

        # 左侧两轮速度（m/s）
        fl = left
        al = left
        # 右侧两轮速度（m/s）
        fr = right
        ar = right

        # 将速度(m/s)转成tick，即PID每个周期轮子要走多少tick数。
        self.v_des_front_left  = int(fl * self.ticks_per_meter / self.arduino.PID_RATE)
        self.v_des_after_left  = int(al * self.ticks_per_meter / self.arduino.PID_RATE)
        self.v_des_front_right = int(fr * self.ticks_per_meter / self.arduino.PID_RATE)
        self.v_des_after_right = int(ar * self.ticks_per_meter / self.arduino.PID_RATE)

        

    

    
