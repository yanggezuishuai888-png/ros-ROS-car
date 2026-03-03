#!/usr/bin/python3

"""
大致流程：
    这个函数分为两个类，一个用来做识别结果的判断与处理（Result_handle），
    另一个用来播报语音（Broadcast_class）。具体就是Result_handle首先
    会做一些初始化的工作以及加载模型，然后一直订阅‘asr_result’的结果，
    回调函数中会判断是哪一类结果，有闲聊、前后左右、导航，闲聊的话就直接
    调用Broadcast_class做播报（新开线程进行播报，同时对数据进行合成，
    每合成一段就播报一段的）
"""

import queue
import threading
import time
import sys
import re 
import numpy as np
from geometry_msgs.msg import Twist 
import rospy
from std_msgs.msg import String
from std_msgs.msg import Bool 
import sounddevice as sd
import sherpa_onnx


# 识别结果处理类
class Result_handle:
    def __init__(self):
        # 只有先初始化ros节点，才可以获取参数（注：模型在这里加载比较好，如果放在下面那个类的话，除非都用全局变量，不然每次调用都得加载一次模型，很慢）
        rospy.init_node("voice_tts", anonymous=False)           # 初始化ros节点
        # 基本参数设置
        self.vits_model = rospy.get_param("~vits_model", "")
        self.vits_lexicon = rospy.get_param("~vits_lexicon", "")
        self.vits_tokens = rospy.get_param("~vits_tokens", "")
        self.vits_data_dir = rospy.get_param("~vits_data_dir", "")
        self.vits_dict_dir = rospy.get_param("~vits_dict_dir", "")
        self.tts_rule_fsts = rospy.get_param("~tts_rule_fsts", "")
        self.save_sound = rospy.get_param("~save_sound", False)  # 是否保存音频文件（否）
        self.sid = rospy.get_param("~sid", 0)
        self.debug = rospy.get_param("~debug", False)
        self.provider = rospy.get_param("~provider", "cpu")
        self.num_threads = rospy.get_param("~num_threads", 1)
        self.speed = rospy.get_param("~speed", 1.0)

        #   发布消息线程两变量
        self.publisher_thread = None                             # 线程对象
        self.publisher_stop = threading.Event()                  # 实例化threading.Event对象。用于控制线程开关

    # 2.模型加载函数
    def load_model(self):
        # rospy.loginfo("Loading TTS model...")
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=self.vits_model,
                    lexicon=self.vits_lexicon,
                    data_dir=self.vits_data_dir,
                    dict_dir=self.vits_dict_dir,
                    tokens=self.vits_tokens,
                ),
                provider=self.provider,
                debug=self.debug,
                num_threads=self.num_threads,
            ),
            rule_fsts=self.tts_rule_fsts,
            max_num_sentences=1,
        )
        if not tts_config.validate():
            rospy.logerr("Invalid TTS configuration. Please check the parameters.")
            sys.exit(1)

        tts = sherpa_onnx.OfflineTts(tts_config)
        self.sample_rate = tts.sample_rate
        rospy.loginfo("TTS model load success.")

        return tts


    # 控制函数：
    #   航点信息发布函数
    def navi_result_cb(self, msg):
        if msg.data == "done":
            # 播报到达
            self.broadcast_bool(f"到达导航点{self.current_wp}啦")      # 进行播报调用
            rospy.loginfo(f"导航点{self.current_wp}到达")

    #   方向消息发布
    def handle_direction(self, dir_str):
        self.reply = ""                                               # 播报的内容
        # 创建 Twist
        tw = Twist()
        duration = 1.5                                                # 运动时间
        speed = 0.2                                                   # 线速度 m/s
        turn = 0.5                                                    # 角速度 rad/s

        if dir_str == "前":
            tw.linear.x = speed
            # self.generate_and_play("好的，向前走")
            self.reply = "好的，向前走"
        elif dir_str == "后":
            tw.linear.x = -speed
            # self.generate_and_play("好的，向后退")
            self.reply = "好的，向后退"
        elif dir_str == "左":
            tw.angular.z = turn
            # self.generate_and_play("好的，向左转")
            self.reply = "好的，向左转"
        elif dir_str == "右":
            tw.angular.z = -turn
            # self.generate_and_play("好的，向右转")
            self.reply = "好的，向右转"

        # 进行播报调用
        self.broadcast_bool(self.reply)

        # 发布运动消息
        end_time = rospy.Time.now() + rospy.Duration(duration)          # 计算出运动时间
        rate = rospy.Rate(10)
        while rospy.Time.now() < end_time and not rospy.is_shutdown():  # 确保在时间范围内且节点不关闭
            self.cmd_pub.publish(tw)
            rate.sleep()
        # 停止
        self.cmd_pub.publish(Twist())
        # rospy.loginfo(f"完成 {dir_str} 控制")
    
    # 3.接收到语音识别消息的回调函数
    def text_callback(self, msg):

        # （1）消息去重处理（只订阅新消息，忽略和上一条完全相同的）
        text = msg.data.strip()                                         # 文本进行去掉首位空白字符。包括空格等
        if text == self.last_text:
            return
        self.last_text = msg.data

        # （2）‘退出’处理（如果接受到的消息为‘退出’，那就让语音识别节点退出）
        if msg.data == '退出':
            self.broadcast_bool('好的，那我先退下了')                       # 播报退出
            self.publisher_thread_fun('-1')                              # 让语音识别退出
            time.sleep( 3 )
            # 关闭tts节点
            rospy.signal_shutdown('退出节点')
        # 多加一个静默输出
        if msg.data == '静默退出':
            self.broadcast_bool('识别到您长时间未讲话，我暂时退下啦')          # 播报退出
            self.publisher_thread_fun('-1')                              # 让语音识别退出
            time.sleep( 3 )
            # 关闭tts节点
            rospy.signal_shutdown('退出节点')
            
        # （3）匹配“导航点N”处理
        m = re.match(r"导航点(\d+)", text)                                # 匹配text中的数字
        if m:
            wp = m.group(1)                                              # 将m中的数字取出
            # 进行播报调用
            self.broadcast_bool(f"好的，立马前往导航点{wp}")
            # 发布导航点
            navi_msg = String(data=wp)                                   # 组织数据
            self.navi_pub.publish(navi_msg)                              # 发布结果
            # rospy.loginfo(f"发布导航点 {wp}")
            return

        # （4）匹配方向处理
        if text in ["前", "后", "左", "右"]:
            self.handle_direction(text)
            return
        
        # （5）正常文本处理
        rospy.loginfo(f"接收到文本： {msg.data}")
        
        # 进行播报调用
        self.broadcast_bool(msg.data)

    # 播报让语音识别停止函数
    def broadcast_bool(self, text):                                      # text : 播报的文本

        global broadcast_thread

        self.publisher_thread_fun('0')                                   # 让语音识别暂停

        # 调用播报,开始播报语音识别结果
        broadcast_class = Broadcast_class(text, self.tts, self.sid, self.speed, self.sample_rate)  
        broadcast_class.start()
        
        # 如果播报完了，就重新开启
        while broadcast_thread.is_alive() and not rospy.is_shutdown():
            rospy.sleep(1)
        self.publisher_thread_fun('1')                                   # 让语音识别开启

    # 消息发布线程函数
    def publisher_thread_fun(self, result):
        # 如果已经有线程在跑，先让它停、等它停
        if self.publisher_thread and self.publisher_thread.is_alive():   # 查看线程是有值，并且是否有在运行
            self.publisher_stop.set()                                    # 停止正在运行的线程（将其设置为False）
            self.publisher_thread.join()                                 # 等原有线程跑完对应函数再退出

        # 开新线程
        self.publisher_stop = threading.Event()
        self.publisher_thread = threading.Thread(
            target=self.publish_loop,
            args=(result, self.publisher_stop),
            daemon=True
        )
        # 让线程开始工作
        self.publisher_thread.start()


    # 消息发布函数
    def publish_loop(self, result, stop_event):
        # 向语音合成发布识别结果
        msg = String()
        msg.data = result 
        rate = rospy.Rate(1)
        rospy.loginfo(f"已向asr发布命令 ---- {msg.data}")
        print('\n')
        # 循环发布(后者是线程，当调用stop_event.set（）就会关闭这一轮循环)
        while not rospy.is_shutdown() and not stop_event.is_set():
            self.asr_pub.publish(result)
            rate.sleep()

    # 开始调用
    def start(self):
         # 加载TTS模型一次
        self.tts = self.load_model()  

        # 创建发布者对象，用于向语音识别节点发布开始，结束信息
        self.asr_pub = rospy.Publisher("voice_asr", String, queue_size=10)
        # 创建发布者对象，用于发布航点命令
        self.navi_pub = rospy.Publisher("/waterplus/navi_waypoint", String, queue_size=10)
        # 创建发布者对象，用于发布运动信息
        self.cmd_pub  = rospy.Publisher("/cmd_vel", Twist, queue_size=10)
        
        # 创建订阅者对象，用于订阅到结果信息
        rospy.Subscriber("/waterplus/navi_result", String, self.navi_result_cb, queue_size=1)
        # 1.创建订阅着对象
        self.last_text = None # 用于去重
        text_topic = rospy.get_param("~text_topic", "asr_result")
        rospy.Subscriber(text_topic, String, self.text_callback, queue_size=1)

        # 开启语音识别
        self.publisher_thread_fun('1')  
        
        rospy.spin()  # 让主线程卡在这，循环接收回调函数


# 播报类
class Broadcast_class:
    def __init__(self, text, tts, sid, speed, sample_rate):
        #  播报线程对应变量。因为上面要调用，因此设置为全局变量
        global broadcast_thread, broadcast_stop
        broadcast_thread = None  # 线程对象  
        broadcast_stop = threading.Event()   # 控制是否开启

        # 模型的一些基本参数
        self.text = text  # 待合成文本
        self.tts = tts  # 模型对象
        self.sid= sid  # 声线ID
        self.speed= speed  # 语速
        self.sample_rate = sample_rate  # 模型采样率

        # 其他参数
        self.first_message_time = None  # 时间
        

    # 播报线程函数
    def broadcast_thread_fun(self):
        global broadcast_thread, broadcast_stop
        # 如果已经有线程在跑，先让它停、等它停
        if broadcast_thread and broadcast_thread.is_alive():  # 查看线程是有值，并且是否有在运行
            broadcast_stop.set()                              # 停止正在运行的线程（将其设置为False）
            broadcast_thread.join()                           # 等原有线程跑完对应函数再退出

        # 开新线程
        broadcast_stop = threading.Event()
        broadcast_thread = threading.Thread(
            target=self.play_audio,                           # 播报语音函数
            args=(broadcast_stop, ),
            daemon=True
        )
        broadcast_thread.start()

    # 4-1每生成一段PCM的回调函数
    def generated_audio_callback(self, samples: np.ndarray, progress: float):
        """This function is called whenever audio samples are generated."""
        if self.first_message_time is None:
            self.first_message_time = time.time()

        self.buffer.put(samples)                             # 存储PCM

        # 如果第一次接受到，就打印第一次
        if not self.started:
            rospy.loginfo("Start playing audio...")
        self.started = True

        # 1 means to keep generating, 0 means to stop generating
        if self.killed:
            return 0

        return 1

    # 4-3将生成的PCM数据分块填充给声卡
    def play_audio_callback(self, outdata: np.ndarray, frames: int, time, status: sd.CallbackFlags):
        global broadcast_stop
        # 判断是否完全播报完毕(TTS模型是否全部生成完，PCM数据队列是否清空)
        if self.killed or (self.started and self.buffer.empty() and self.stopped):
            # self.event.set()
            broadcast_stop.set()

        # 如果队列时空的，就播报静音
        if self.buffer.empty():
            outdata.fill(0)
            return

        # 从队列中将数据填满
        n = 0
        while n < frames and not self.buffer.empty():
            remaining = frames - n
            k = self.buffer.queue[0].shape[0]

            if remaining <= k:
                outdata[n:, 0] = self.buffer.queue[0][:remaining]
                self.buffer.queue[0] = self.buffer.queue[0][remaining:]
                n = frames
                if self.buffer.queue[0].shape[0] == 0:
                    self.buffer.get()
                break

            outdata[n : n + k, 0] = self.buffer.get()
            n += k

        if n < frames:
            outdata[n:, 0] = 0

    # 4-2进行播报并发送播报状态
    def play_audio(self, broadcast_stop):
        # 打开声卡设备、启动内部线程，持续调用回调函数。
        try:
            if not rospy.is_shutdown() and not broadcast_stop.is_set():  # 确保节点不关闭和
                with sd.OutputStream(  
                    channels=1,  # 单声道
                    callback=self.play_audio_callback,                   # 每当声卡请求下一块PCM数据时，就调用回调函数（播放）
                    dtype="float32",
                    samplerate=self.sample_rate,                         # 模型采样率（合成和播放一致）
                    blocksize=1024,                                      # 声卡每次拉取1024帧数据。当帧数不足时回调填充静音
                ):
                    broadcast_stop.wait()                                # 让该线程处于等待状态，直到调用self.event.set（上面的回调会新开一个线程）

        finally:
            rospy.loginfo("音频已结束播放")
    
    # 开始调用
    def start(self):
        # 重置播放相关状态
        self.buffer = queue.Queue()
        self.started = False
        self.stopped = False
        self.killed = False

        # 播报线程函数（进行播报）
        self.broadcast_thread_fun()

        # 调用TTS模型合成音频
        rospy.loginfo("正在合成")
        #   将文本转为PCM数据（合成）
        audio = self.tts.generate(
            self.text,  # 待合成文本
            sid=self.sid,  # 声线ID
            speed=self.speed,  # 语速
            callback=self.generated_audio_callback,                     # 每生成一段PCM就会回调该函数
        )
        
        self.stopped = True                                             # 表示生成结束（告诉线程后续没有新数据）


if __name__ == "__main__":

    result_handle = Result_handle()
    result_handle.start()

