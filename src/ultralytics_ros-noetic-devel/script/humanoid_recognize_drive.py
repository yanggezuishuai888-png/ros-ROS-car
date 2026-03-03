#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    这代码是人形追踪代码。首先订阅/usb_cam/image_rect_color/compressed图像
    进行人形识别，识别结果通过/yolo_image_humanoid发布。拿到框信息后进行测距，
    第一次获取最近的人并记录id，后续持续跟着该id的框，接着根据前后距离、左右偏移
    误差控制小车。
"""

import cv2
import cv_bridge
import numpy as np
import roslib.packages
import rospy
from sensor_msgs.msg import Image
from ultralytics import YOLO
from geometry_msgs.msg import Twist
from sensor_msgs.msg import CompressedImage



class TrackerNode:
    def __init__(self):
        yolo_model = rospy.get_param("~yolo_model", "yolov8n.pt")
        self.input_topic = rospy.get_param("~input_topic", "image_raw")
        self.result_topic = rospy.get_param("~result_topic", "yolo_result")
        self.result_image_topic = rospy.get_param("~result_image_topic", "yolo_image")
        self.conf_thres = rospy.get_param("~conf_thres", 0.25)
        self.iou_thres = rospy.get_param("~iou_thres", 0.45)
        self.max_det = rospy.get_param("~max_det", 300)
        self.classes = rospy.get_param("~classes", None)
        self.tracker = rospy.get_param("~tracker", "bytetrack.yaml")
        self.device = rospy.get_param("~device", None)
        self.result_conf = rospy.get_param("~result_conf", True)
        self.result_line_width = rospy.get_param("~result_line_width", None)
        self.result_font_size = rospy.get_param("~result_font_size", None)
        self.result_font = rospy.get_param("~result_font", "Arial.ttf")
        self.result_labels = rospy.get_param("~result_labels", True)
        self.result_boxes = rospy.get_param("~result_boxes", True)
        path = roslib.packages.get_pkg_dir("ultralytics_ros")
        self.model = YOLO(f"{path}/models/{yolo_model}")
        self.model.fuse()                                                                                         # 融合BN 提速
        self.sub = rospy.Subscriber(self.input_topic, CompressedImage, self.image_callback, 
                                    queue_size=1, buff_size=2**24,)                                               # 图像订阅
        self.cmd_pub = rospy.Publisher("cmd_vel", Twist, queue_size=1)                                            # 控制小车
        self.result_image_pub  = rospy.Publisher(self.result_image_topic, Image, queue_size=1)                    # 处理后图像
        self.bridge = cv_bridge.CvBridge()                                                                        # cv实例化
        self.target_id = None                                                                                     # 当前锁定的目标ID
    # 图像订阅回调
    def image_callback(self, msg):
        # 解压并转换图像
        np_arr = np.frombuffer(msg.data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)   # 转cv
        if cv_image is None:
            rospy.logwarn("Decode failed!")
            return

        # 做检测
        results = self.model.track(
            source=cv_image,
            conf=self.conf_thres,
            iou=self.iou_thres,
            max_det=self.max_det,
            classes=self.classes,
            tracker=self.tracker,
            device=self.device,
            verbose=False,
            retina_masks=True,
        )

        if results is not None:
            dis_m = self.goal_depth(results)                            # 控制小车
            yolo_result_image_msg = Image()                             # 组织图像数据
            yolo_result_image_msg = self.create_result_image(results)   # 图像处理（框出目标）
            yolo_result_image_msg.header = msg.header                   # 增加头（父级坐标系）
            self.result_image_pub.publish(yolo_result_image_msg)
            if dis_m is None:
                rospy.logwarn("未检测到 person")
                return

    # 获取距离及控制小车
    def goal_depth(self, results):
        # ===== 相机 & 目标参数 =====
        fy = 461.81736              # 焦距f
        real_height_m = 1.60        # 物体高度
        pixel_margin = 2            # h-2，避免边界不贴合
        target_dist = 2.0           # 期望跟随距离（米）

        # ===== 控制参数 =====
        k_v = 0.5                   # 前进比例系数
        k_w = 0.004                 # 转向比例系数
        max_v = 0.6                 # 最大线速度
        max_w = 0.8                 # 最大角速度

        if results is None or len(results) == 0 or results[0].boxes is None or len(results[0].boxes) == 0:
            return None

        # 获取框信息
        boxes = results[0].boxes
        cls = boxes.cls
        xywh = boxes.xywh  

        # torch转numpy
        cls_np = cls.cpu().numpy() if hasattr(cls, "cpu") else np.asarray(cls)          # 类别数组
        xywh_np = xywh.cpu().numpy() if hasattr(xywh, "cpu") else np.asarray(xywh)      # 框几何信息

        # 获取类别为0（行人）序号
        person_idx = np.where(cls_np.astype(int) == 0)[0]                               
        if person_idx.size == 0:
            rospy.logwarn("没有目标标签")
            self.target_id = None
            return None
        
        # 获取 track_id
        track_ids = boxes.id
        if track_ids is None:
            return None
        # 框列表
        track_ids_np = track_ids.cpu().numpy().astype(int)
        if self.target_id is None:
            # 第一次：选最近的人
            h_all = xywh_np[person_idx, 3].astype(float)
            best_local = int(np.argmax(h_all))
            best_idx = int(person_idx[best_local])
            self.target_id = int(track_ids_np[best_idx])
            rospy.loginfo(f"Lock target_id={self.target_id}")
        else:
            # 追踪上次识别到的框序号
            match_idx = np.where(track_ids_np == self.target_id)[0]

            if match_idx.size == 0:
                rospy.logwarn(f"Target {self.target_id} lost!")
                self.target_id = None
                return None
            # 找到锁定目标对应的框序号
            best_idx = int(match_idx[0])

        # 修剪框高。框一般不贴合人
        h_px = float(xywh_np[best_idx, 3]) - pixel_margin   
        if h_px <= 1.0:
            return None

        # 获取目标中心水平位置
        cx = float(xywh_np[best_idx, 0]) 
        
        # 计算目标距离（相似三角形原理）
        dist = (real_height_m * float(fy)) / h_px          
        
       # ===== 运动控制（和颜色跟随一模一样）=====
        img_cx = 640 / 2.0                  # 图像中心（按你的分辨率）
        err_dist = dist - target_dist       # 距离误差
        err_x = img_cx - cx                 # 水平偏差

        v = k_v * err_dist                  # 前进速度
        w = k_w * err_x                     # 转弯速度

        # 限幅
        v = max(-max_v, min(max_v, v))
        w = max(-max_w, min(max_w, w))

        # 发布速度
        cmd = Twist()
        cmd.linear.x = v
        cmd.angular.z = w
        self.cmd_pub.publish(cmd)

        rospy.loginfo(f"dist={dist:.2f}m, v={v:.2f}, w={w:.2f}")

        return float(dist)

    # 在图像中框出目标
    def create_result_image(self, results):
        # ultralytics自带话题函数
        plotted_image = results[0].plot(
            conf=self.result_conf,              # 置信度
            line_width=self.result_line_width,  # 线粗细
            font_size=self.result_font_size,    # 字体大小
            font=self.result_font,              # 字号
            labels=self.result_labels,          # 字体类别
            boxes=self.result_boxes,            # 画框
        )
        result_image_msg = self.bridge.cv2_to_imgmsg(plotted_image, encoding="bgr8")
        return result_image_msg


if __name__ == "__main__":
    rospy.init_node("tracker_node")
    node = TrackerNode()
    rospy.spin()
