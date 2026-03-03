#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说明：
    1.每一个手势都有一个延时，延时结束就停止小车。其中，前进、后退时间为2s，转弯（左、右）为5s，转弯为10s。
      另外， 线速度、角速度都需要封装好接口，默认为0.3、0.4 
    2.在做完动作之后，如果没有检测到手势，需要以0.4角速度逆时针转弯，直到检测到手势 
    3.不需要计算让目标置于小车中间，但是需要对目标进行测距，如果距离需要在
      1-5m之间，超过这个区间，再控制小车前进、后退则无效。
思路：
    首先回调执行，检测到手势标签就执行动作，同时持续识别手势，
    如果小车执行动作，就不使用该手势，仅发布识别结果。另外ros
    时钟时刻回调，执行时间到了停止小车，然后判断是否有手势，没有就转弯
    
"""

import math
import cv2
import cv_bridge
import numpy as np
import rospy
import roslib.packages

from ultralytics import YOLO
from geometry_msgs.msg import Twist
from sensor_msgs.msg import CompressedImage, Image


class GestureControlNode:
    # ====== 状态 ======
    # STATE_IDLE = 0        # 等待手势（检测到就执行）
    # STATE_ACTION = 1      # 正在执行动作（持续时间内保持速度）
    # STATE_SEARCH = 2      # 动作完成后没检测到手势：原地逆时针搜
    standby = 0             # 待机
    in_progress  = 1        # 执行中
    search       = 2        # 搜索手势
    def __init__(self):
        # ===== ROS params =====
        yolo_model = rospy.get_param("~yolo_model", "gesture.pt")
        self.input_topic = rospy.get_param("~input_topic", "/usb_cam/image_rect_color/compressed")
        self.cmd_topic = rospy.get_param("~cmd_topic", "cmd_vel")
        self.result_image_topic = rospy.get_param("~result_image_topic", "yolo_image_gesture")

        self.conf_thres = float(rospy.get_param("~conf_thres", 0.25))
        self.iou_thres = float(rospy.get_param("~iou_thres", 0.45))
        self.max_det = int(rospy.get_param("~max_det", 50))
        self.device = rospy.get_param("~device", None)
        self.classes = rospy.get_param("~classes", None)                     # 例如 [0,1,2,3,4,5,6,7] 或 None
        path = roslib.packages.get_pkg_dir("ultralytics_ros")

        # 速度接口（默认）
        self.linear_speed = float(rospy.get_param("~linear_speed", 0.3))
        self.angular_speed = float(rospy.get_param("~angular_speed", 0.4))
        # 搜索手势用的逆时针角速度（默认 0.4）
        self.search_angular_speed = float(rospy.get_param("~search_angular_speed", 0.4))

        # 动作时长
        self.t_forward_back = float(rospy.get_param("~t_forward_back", 2.0))
        self.t_turn = float(rospy.get_param("~t_turn", 5.0))
        self.t_spin = float(rospy.get_param("~t_spin", 10.0))

        # 测距参数
        self.fy = float(rospy.get_param("~fy", 461.81736))
        self.real_height_m = float(rospy.get_param("~real_height_m", 0.15))  # 手真实高度
        self.pixel_margin = float(rospy.get_param("~pixel_margin", 0.0))     # 框高度修剪
        self.min_dist = float(rospy.get_param("~min_dist", 1.0))             # 小车运行区间
        self.max_dist = float(rospy.get_param("~max_dist", 5.0))

        # 选择“最佳手势框”的策略：conf 或 area
        self.best_by = rospy.get_param("~best_by", "conf")  # "conf" / "area"

        # 发布频率（保证：即使相机卡顿也能按时停车、搜手势）
        self.control_rate = float(rospy.get_param("~control_rate", 20.0))

        # ===== Load YOLO model =====
        model_path = YOLO(f"{path}/models/{yolo_model}")
        self.model = YOLO(model_path)
        try:
            self.model.fuse()
        except Exception:
            pass

        # ===== ROS pub/sub =====
        self.bridge = cv_bridge.CvBridge()
        self.sub = rospy.Subscriber(
            self.input_topic,
            CompressedImage,
            self.image_callback,
            queue_size=1,
            buff_size=2**24
        )
        self.cmd_pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        self.result_image_pub = rospy.Publisher(self.result_image_topic, Image, queue_size=1)

        # ===== 控制状态变量 =====
        self.state = self.standby               # 状态控制变量
        self.current_cmd = Twist()
        self.action_end_time = rospy.Time(0)
        self.last_gesture_seen = False          # 是否检测到手势
        self.last_gesture_id = None             # 手势lable
        self.last_gesture_dist = None

        # ROS自带时钟，每隔1/self.control_rate调用函数。
        # 注：时钟回调和图像订阅回调都是单开线程，并发执行
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.control_rate), self.control_loop)

        rospy.loginfo("GestureControlNode started.")
        rospy.loginfo(f"Model: {model_path}")
        rospy.loginfo(f"Input: {self.input_topic} -> Cmd: {self.cmd_topic}")

    # ===== ROS时钟回调函数（根据状态量决定动作。包括：正在执行、待机、不可执行） =====
    def control_loop(self, _ret):
        now = rospy.Time.now()
        # 动作正在执行
        if self.state == self.in_progress:                      
            # 时间没到就一直发布
            if now < self.action_end_time: 
                self.publish_cmd()
                return
            # 执行时间到了就停止
            self.set_cmd(0.0, 0.0)
            self.publish_cmd()
            # 没有手势就搜索
            if not self.last_gesture_seen:                  
                # self.state = self.search
                pass
            else:
                self.state = self.standby  # 待机

        # 转圈寻找手势
        elif self.state == self.search:
            # 有手势就停并回到待机
            if self.last_gesture_seen:
                self.set_cmd(0.0, 0.0)
                self.publish_cmd()
                self.state = self.standby
            else:
                self.set_cmd(0.0, +abs(self.search_angular_speed))
                self.publish_cmd()

    # ===== 图像回调：做 YOLO 推理、测距、决定是否触发动作 =====
    def image_callback(self, msg: CompressedImage):
        # 解码图像
        np_arr = np.frombuffer(msg.data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if cv_image is None:
            rospy.logwarn("Decode failed!")
            self.last_gesture_seen = False
            return

        # YOLO 推理（detect即可）
        results = self.model.track(
            source=cv_image,
            conf=self.conf_thres,
            iou=self.iou_thres,
            max_det=self.max_det,
            classes=self.classes,
            device=self.device,
            verbose=False
        )

        # 选出质量最高的框并计算距离
        gesture_id, dist_m = self.pick_best_gesture_and_distance(results)
        self.last_gesture_seen = (gesture_id is not None)                   # 记录识别到手势
        self.last_gesture_id = gesture_id
        self.last_gesture_dist = dist_m

        # 发布可视化图像
        self.publish_result_image(results, msg.header)

        # 没有框退出
        if gesture_id is None:
            return
        # 动作正在执行或者搜索就退出就退出
        if (self.state == self.in_progress) or (self.state == self.search):
            return
        # 触发动作
        self.try_start_action(gesture_id, dist_m)

    # ===== 从结果中选一个最佳手势，并测距 =====
    def pick_best_gesture_and_distance(self, results):
        if results is None or len(results) == 0:
            return None, None
        r0 = results[0]
        if r0.boxes is None or len(r0.boxes) == 0:
            return None, None

        boxes = r0.boxes
        cls = boxes.cls
        conf = boxes.conf
        xyxy = boxes.xyxy

        # torch转numpy
        cls_np = cls.cpu().numpy() if hasattr(cls, "cpu") else np.asarray(cls)
        conf_np = conf.cpu().numpy() if hasattr(conf, "cpu") else np.asarray(conf)
        xyxy_np = xyxy.cpu().numpy() if hasattr(xyxy, "cpu") else np.asarray(xyxy)

        # area
        wh = xyxy_np[:, 2:4] - xyxy_np[:, 0:2]
        area_np = (wh[:, 0] * wh[:, 1]).astype(float)

        # best index
        if self.best_by == "area":
            best_i = int(np.argmax(area_np))
        else:
            best_i = int(np.argmax(conf_np))

        gesture_id = int(cls_np[best_i])

        # 用框高度做单目测距
        h_px = float(wh[best_i, 1]) - float(self.pixel_margin)
        if h_px <= 1.0:
            return gesture_id, None

        dist = (self.real_height_m * float(self.fy)) / h_px
        return gesture_id, float(dist)

    # ===== 启动动作 =====
    def try_start_action(self, gesture_id: int, dist_m):
        now = rospy.Time.now()

        # 如果label是前后并且在距离之外就停止小车（映射）
        if (dist_m <= self.min_dist and gesture_id == 1) or (dist_m >= self.max_dist and gesture_id == 0):
            rospy.logwarn("距离不在1~5m，前进/后退无效")
            gesture_id = 2
            return
        else:
            # 映射速度与时长
            v, w, duration = self.map_gesture_to_cmd(gesture_id)

        # 开始执行动作
        self.set_cmd(v, w)
        self.publish_cmd()
        self.state = self.in_progress                          # 动作正在执行 
        self.action_end_time = now + rospy.Duration(duration)  # 记录动作执行时间

        rospy.loginfo(f"识别到的标签：{gesture_id}, 距离：{dist_m:.2f}, v={v:.2f}, w={w:.2f}, t={duration:.1f}s")

    # ===== 根据label映射执行时间、速度信息 =====
    def map_gesture_to_cmd(self, gesture_id: int):
        """
        返回 (linear_x, angular_z, duration_s)
        """
        v = 0.0
        w = 0.0
        t = 0.0

        # 后退：0（2s）
        if gesture_id == 0:
            v = -abs(self.linear_speed)
            w = 0.0
            t = self.t_forward_back

        # 前进：1（2s）
        elif gesture_id == 1:
            v = +abs(self.linear_speed)
            w = 0.0
            t = self.t_forward_back

        # 停止：2（立即）
        elif gesture_id == 2:
            v = 0.0
            w = 0.0
            t = 0.0

        # 转圈：3（10s）——原地持续转
        elif gesture_id == 3:
            v = 0.0
            w = +abs(self.angular_speed)
            t = self.t_spin

        # 左前方：4（5s）
        elif gesture_id == 4:
            v = +abs(self.linear_speed)
            w = +abs(self.angular_speed)
            t = self.t_turn

        # 右前方：5（5s）
        elif gesture_id == 5:
            v = +abs(self.linear_speed)
            w = -abs(self.angular_speed)
            t = self.t_turn

        # 左后方：6（5s）
        elif gesture_id == 6:
            v = -abs(self.linear_speed)
            w = +abs(self.angular_speed)
            t = self.t_turn

        # 右后方：7（5s）
        elif gesture_id == 7:
            v = -abs(self.linear_speed)
            w = -abs(self.angular_speed)
            t = self.t_turn

        else:
            # 未知label：不动
            v = 0.0
            w = 0.0
            t = 0.0

        return v, w, t

    # ===== 工具函数 =====
    # 设置速度信息
    def set_cmd(self, vx: float, wz: float):
        self.current_cmd.linear.x = float(vx)
        self.current_cmd.angular.z = float(wz)
    # ***************************** 可改 ***************************** 
    def publish_cmd(self):
        self.cmd_pub.publish(self.current_cmd)
    # ***************************** 可改 ***************************** 
    
    # 图像识别结果发布
    def publish_result_image(self, results, header):
        if results is None or len(results) == 0:
            return
        try:
            plotted = results[0].plot()
            img_msg = self.bridge.cv2_to_imgmsg(plotted, encoding="bgr8")
            img_msg.header = header
            self.result_image_pub.publish(img_msg)
        except Exception as e:
            rospy.logwarn(f"Plot/publish image failed: {e}")


if __name__ == "__main__":
    rospy.init_node("gesture_control_node")
    node = GestureControlNode()
    rospy.spin()
