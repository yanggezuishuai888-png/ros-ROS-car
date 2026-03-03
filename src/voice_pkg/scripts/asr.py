#!/usr/bin/env python3
# coding:utf-8

"""
大致流程：
    代码封装成了很多类和两个函数, 分别是ai纠正类、websocket生成URL和验证类、websocket连接创建及语音识别类、
    Job线程类 (整个语音识别) 、callback函数、main函数。具体的流程就是 : 首先就是main中初始化ros节点, 
     (callback函数内) 并持续接收'voice_asr'的消息 (包括开始、暂停、停止) , 分别控制整个语音识别线程和语音
    线程。接收到为开始之后就调用Job线程类去开线程, 用于整个语音的线程。该线程里面会调用websocket连接创建及语
    音识别类 (主要的执行是这个类) , 该类里面又会调用websocket生成URL和验证类, 以及调用那个 'on_oepn' 函数新开
    线程进行语音的录制与发送。服务器返回识别结果之后会调用类里面 'on_message' 对识别结果进行处理。其中会打印结
    果、调用ai纠正类进行语义识别、向 'asr_result' 发送识别后的结果。
    注：
	    (1)打印识别结果时又一次关闭两个线程, 发布结果, 语音合成之后会向'voice_asr'发送暂停, 
        又会暂停两个线程, 这是因为该话题接收消息有去重, 先发暂停, 到时候发开始才能接收到 (不去重它会识别不了的) 
        (2)类调用：接收信息 ---- Job线程 ---- Connect_identify连接与识别总调用 ----  Ws_Param连接 ---- AI纠正 ---- 结果输出
        (3)讯飞等待够时间之后，即使没有输入，也会返回一次结果（空）
"""


import rospy, threading, websocket, hashlib, base64, hmac, json 
import time, ssl, pyaudio, requests, uuid, ssl
from std_msgs.msg import String
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import numpy as np


class AI:

# WebSocket URL和身份验证
class Ws_Param ( object ):
    # 1.基本信息初始化
    def __init__(self, APPID, APIKey, APISecret):
        # 三组件
        self.APPID = ''
        self.APIKey = ''
        self.APISecret = ''

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)。更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat",               # 日常会话
                             "language": "zh_cn",           # 中文
                               "accent": "mandarin",        # 普通话 (方言选项) 
                               "vinfo": 1,                  # 控制是否在返回结果中附带端点检测
                               "vad_eos": 30000}            # 检测到之后60秒关闭连接(毫秒)静默

    # 2.通过时间戳、API Key 和 Secret 生成 WebSocket 连接所需的 URL
    def create_url(self):
        # url = 'wss://ws-api.xfyun.cn/v2/iat'
        url ='wss://iat-api.xfyun.cn/v2/iat'
        # 生成当前的RFC1123格式时间戳
        now = datetime.now ()
        # 时间戳格式为：UTC + 0或 GMT时区。时钟偏差最大允许300秒。超过请求会被拒绝
        date = format_date_time ( mktime ( now.timetuple () ) )

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new ( self.APISecret.encode ( 'utf-8' ), signature_origin.encode ( 'utf-8' ),
                                   digestmod=hashlib.sha256 ).digest ()
        signature_sha = base64.b64encode ( signature_sha ).decode ( encoding='utf-8' )

        # 构建请求参数
        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        
        # 使用base64编码对请求参数进行编码
        authorization = base64.b64encode ( authorization_origin.encode ( 'utf-8' ) ).decode ( encoding='utf-8' )
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,  
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数, 生成url
        url = url + '?' + urlencode ( v )
        return url


# 3.与websocket连接, 并新开线程用于录制、发送语音

# WebSocket连接, 语音识别类
class Connect_identify:
    def __init__(self):
        # 注意：不能将线程变量放在这里，这个会在2秒内没有输入就重新调用的了。每次都初始化，导致每次不满足关掉线程的条件。然后就会一直发
        # #   识别结果发布线程
        # publisher_thread = None  # 线程对象
        # publisher_stop = threading.Event()  # 实例化threading.Event对象。用于控制线程开关
        # #   识别线程
        # identify_thread = None
        # identify_stop = threading.Event()

        # 语音音频的标识
        self.STATUS_FIRST_FRAME = 0                         # 第一帧的标识
        self.STATUS_CONTINUE_FRAME = 1                      # 中间帧标识
        self.STATUS_LAST_FRAME = 2                          # 最后一帧的标识
        
    # 语音识别线程函数
    def identify_thread_fun(self, ws):
        global identify_thread, identify_stop
        # 如果已经有线程在跑, 先让它停、等它停
        if identify_thread and identify_thread.is_alive():  # 查看线程是有值, 并且是否有在运行
            identify_stop.set()                             # 停止正在运行的线程 (将其设置为False) 
            identify_thread.join()                          # 等原有线程跑完对应函数再退出

        # 开新线程
        identify_stop = threading.Event()
        identify_thread = threading.Thread(
            target=self.identify,
            args=(ws, identify_stop),
            daemon=True
        )

        identify_thread.start()

    # 5.开启一个线程去发布识别结果

    # 识别结果发布线程函数
    def pub_thread_fun(self, result):
        global publisher_stop, publisher_thread
        # 如果已经有线程在跑, 先让它停、等它停
        if publisher_thread and publisher_thread.is_alive():  # 查看线程是有值, 并且是否有在运行
            publisher_stop.set()                              # 停止正在运行的线程 (将其设置为False) 
            publisher_thread.join()                           # 等原有线程跑完对应函数再退出

        # 开新线程
        publisher_stop = threading.Event()
        publisher_thread = threading.Thread(
            target=self.publish_loop,                         # 绑定的函数
            args=(result, publisher_stop),                    # 传入的参数
            daemon=True                                       # 设置为守护线程
        )
        publisher_thread.start()                              # 让线程开始工作

    # 6.发布识别结果

    # 识别结果发布函数
    def publish_loop(self, result, stop_event):
        global pub
        # 向语音合成发布识别结果
        msg = String()
        msg.data = result 
        rate = rospy.Rate(1)
        # rospy.loginfo('循环发布识别结果')
        print('\n')
        # 循环发布(后者是线程, 当调用stop_event.set () 就会关闭这一轮循环)
        while not rospy.is_shutdown() and not stop_event.is_set():
            pub.publish(result)
            rate.sleep()

    # 语音识别函数
    def identify(self, ws, stop_event):

            status = self.STATUS_FIRST_FRAME                  # 音频的状态信息, 标识音频是第一帧, 还是中间帧、最后一帧
            CHUNK = 520                                       # 数字信号读取个数频率。帧数
            FORMAT = pyaudio.paInt16                          # 16bit编码格式
            CHANNELS = 1                                      # 单声道
            RATE = 16000                                      # 模拟信号采样个数频率。采样率
            # 实例化pyaudio对象
            p = pyaudio.PyAudio ()  # 录音
            
            DEVICE_INDEX = 6   # 改成你查到的 index

            # 打开音频流
            # 使用这个对象去打开声卡, 并根据设定的参数，将读取到的音频数据转换成PCM数据

            stream = p.open ( format=FORMAT,                   # 音频流wav格式
                            channels=CHANNELS,                 # 单声道
                            rate=RATE,                         # 采样率16000
                            input=True,                        # 打开输入通道
                            input_device_index=DEVICE_INDEX,   # 指定麦克风设备号
                            frames_per_buffer=CHUNK )          # 数据流块

            """
            作用: 
                循环录制音频数据, 持续60秒。
            
            解析：
                这个是固定时间写法。int ( RATE / CHUNK * 60 )的值为1846, 即读取1846次, 每次读取520。
                总得样本数就是960000 (缓冲区样本数, 也是对模拟信号采集到的数字样本数) .总样本数/频率=录制时间。
            注意：
                这个虽然是固定时间, 但他并不是固定时间发送的。而是一边讲一边发送, 讲完过了n秒 (最上面有设置) 就断开连接了
            """
            SILENCE_THRESHOLD = 100                             # 沉默音量最低阈值 (有声音一般会超过100) 
            SILENCE_FRAMES    = 1250                            # 沉默时间阈值 (625对应20秒) 沉默超过这个时间就会退出 (重新进入函数会重置) 
            silence_count     = 0                               # 沉默次数

            # 只要子线程开着, 这里就一直进行语音识别
            while voice_thread and not stop_event.is_set():

                """
                原理：
                    打开录音流之后就会有数据到缓冲区, 每次读取缓冲区, 刚开始让帧数为第一帧,用来第一次发送id
                    和businessargs这两参数,发送之后将帧数置为中间帧,然后一直读取缓冲区, 读取一次发送一次。直到循环结束
                """
                # 读出声卡缓冲区的音频数据，长度为CHUNK
                buf = stream.read ( CHUNK )                     # 注：这里并不知道多少个CHUNK是一句话, 他只负责将数据发送, 至于哪里是读完一句话, 讯飞会识别。在识别出读完一句话之后, 讯飞会立马将识别结果返回

                # 检查是否为静默阀值
                pcm = np.frombuffer(buf, np.int16)              # 转成 int16的numpy 数组
                amp = np.abs(pcm).mean()

                # rospy.loginfo(f"音量绝对值:{amp}")

                if amp < SILENCE_THRESHOLD:                     # 计算均值判断是否小于阈值
                    silence_count += 1
                else:
                    silence_count = 0

                if silence_count >= SILENCE_FRAMES:             # 超过静默次数就退出
                    rospy.loginfo("多次检测到沉默, 退出识别会话")
                    self.pub_thread_fun('静默退出')
                    break

                # 如果buf为空, 那就将音频设置最后一帧, 表示结束。
                # 注：正常来说缓冲区会一直有数据 (那怕声音环境音量很小, 但还是会采集到的) , 因此不会进入最后一帧
                if not buf:
                    status = self.STATUS_LAST_FRAME
                    print('********现在是最后一帧*********')
                try:
                    # 第一帧发送
                    if status == self.STATUS_FIRST_FRAME:
                        # 刚开始需要id和businessargs这两个参数
                        d = {"common": wsParam.CommonArgs,                                # id
                            "business": wsParam.BusinessArgs,                             # businessargs (语音识别基本参数)   
                            "data": {"status": 0,                                         # 表示第一帧 (初始化回话) 
                                    "format": "audio/L16;rate=16000",  # 音频格式。这个表示PCM 16-bit、16000Hz
                                    "audio": str ( base64.b64encode ( buf ), 'utf-8' ),   # 将原始PCM数据做Base64编码, 再转成UTF-8字符串, 方便发送 (WebSocket只能发字符串) 
                                    "encoding": "raw"}}                                   # 跟服务器说明原本编码格式。到时候用pcm方式解码
                        
                        d = json.dumps ( d )  #将字典序列化为json文本
                        ws.send ( d )  # 向webSocket发送数据
                        status = self.STATUS_CONTINUE_FRAME                               # 处理完第一帧后, 设置成中间帧。让中间帧处理函数处理
                    # 中间帧发送
                    elif status == self.STATUS_CONTINUE_FRAME:
                        d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                    "audio": str ( base64.b64encode ( buf ), 'utf-8' ),
                                    "encoding": "raw"}}
                        ws.send ( json.dumps ( d ) )

                    # 最后一帧处理
                    elif status == self.STATUS_LAST_FRAME:
                        d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                    "audio": str ( base64.b64encode ( buf ), 'utf-8' ),
                                    "encoding": "raw"}}
                        ws.send ( json.dumps ( d ) )
                        time.sleep ( 1 )
                        break
                except Exception as e:
                    rospy.logerr(f"⚠️ 音频发送或读取异常: {e}")
                    pass

    # 如果收到的WebSocket的结果是连接成功就录音、编码、发送
    def on_open(self, ws):  # 执行完这个函数后会退出连接
        global voice_thread

        """
        作用：
            子线程里面又开一个小线程 (立即开启的) 。因为这个是连接成功后执行的, 
            因此需要多开一个线程, 这样就可以一边监听服务器, 一边订阅
        函数讲解：
            这是一个低级新开线程方法, 只有调用函数和传入参数两个参数。并且主线程退出时, 他只能强制退出。与上面的threading.Thread相反
        """
        # 检查是否开了语音线程
        if voice_thread:
            self.identify_thread_fun(ws)

    # 4.websocket返回识别结果

    # 当websocket服务端收到消息之后就会调用该处理函数
    #   ws ---- 当前websocket连接对象
    #   message ---- 服务器处理后的原始文本 (json) 
    def on_message(self, ws, message):
        """
        '{"code":0,"message":"success","sid":"iat000d3cee@gz1968f359ae546f9802",
        "data":{"result":{"ed":0,"vad":{"ws":[{"bg":215,"ed":363,"eg":35.71}]},
        "ws":[{"bg":41,"cw":[{"sc":0,"w":"小度小度"}]}],"sn":1,"ls":false,"bg":0},
        "status":0}}'
        """
        global thread_rec
        global voice_thread

        # 提取识别结果
        useless = ['。', '.。', ' .。', ' 。', ', ', ' , ', ',', ' ,', ' , ', ', ', None, ' ']  # 定义结果为无用的东西
        try:
            code = json.loads ( message )["code"]
            sid = json.loads ( message )["sid"]
            # 确认有信息
            if code != 0:
                errMsg = json.loads ( message )["message"]

            # 提取文本
            else:
                data = json.loads ( message )["data"]["result"]["ws"]
                result = ""
                for i in data:
                    for w in i["cw"]:
                        result += w["w"]                  # w是字典
                
                # 判断是否是无用信息
                if result in useless:
                    print("===========识别结果无效") 
                else:
                    rospy.loginfo(f"识别结果:{result}")

                    # 如果识别结果为退出, 那就直接退出识别和合成
                    if result == '退出':
                        self.pub_thread_fun('退出')

                    # 调用ai之前先让暂停整个语音线程。等播报完之后重新开就好了
                    thread_rec.pause()                  # 关掉整个语音线程
                    voice_thread = False                # 关掉语音识别线程
                    rospy.loginfo('语义识别中……')

                    # 调用ai去纠正
                    ai = AI(result)                     # 初始化类
                    ai_result = ai.start()              # 开始调用
                    rospy.loginfo(f' 纠正结果：{ai_result}')
                    # ai_result = result
                    # 调用发布线程去发布结果
                    self.pub_thread_fun(ai_result)

        except Exception as e:
            print ( "receive msg,but parse exception:", e )


    # 如果收到的WebSocket得结果是连接出错, 就打印错误信息
    def on_error(self, ws, error):
        print ( "### error:", error )
        # 关闭连接
        ws.close ()
        # 重启连接
        self.start()


    # 如果收到的WebSocket的结果是关闭, 就pass
    def on_close(self, ws, close_status_code, close_msg):
        # rospy.loginfo('ws调用close函数, 关闭连接')
        pass

    def start(self):
        # 初始化Ws_Param类。初始化连接基本信息
        global wsParam

        wsParam = Ws_Param ( APPID='',
                            APIKey='',
                            APISecret='' )
        # 禁用websocket的调试信息
        websocket.enableTrace ( False )
        # 调用类中函数, 创建URL
        wsUrl = wsParam.create_url ()
        # 实例化连接对象, 里面分别设置有消息 (无论什么消息) 就返回、出错、连接断开对应的回调函数
        ws = websocket.WebSocketApp ( wsUrl, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close )
        # 注册连接成功后的回调函数。连接成功立马调用 (连接成功也叫握手, 一次连接中只会调用一次) 
        ws.on_open = self.on_open

        # 开始并持续连接, 除非手动关闭
        ws.run_forever ( sslopt={"cert_reqs": ssl.CERT_NONE},  # 不验证服务证书
                        ping_timeout=None )  # ping_timeout是服务器没发信息过来就会关闭连接 (调用on_close) , 设置为None表示一直等待(单位-秒)

        # 注：创建连接后该线程会在这执行持续连接, 并一直等待回调。当有回调就会调用对应的回调函数。当主动关闭连接之后又会回到原本job的循环中 


# 多线程控制语音启动、暂停、停止 (这样可以实现重复调用) 
class Job ( threading.Thread ):

    def __init__(self, *args, **kwargs):
        super ( Job, self ).__init__ ( *args, **kwargs )
        # 分别定义两个暂停, 停止线程变量
        self.__flag = threading.Event ()        # 控制暂停和恢复线程
        self.__flag.set ()                      # 设置为True
        self.__running = threading.Event ()     # 控制停止或继续线程
        self.__running.set ()                   # 设置为True

    def run(self):
        global voice_thread  # 语音线程
        
        # 检查控制整个语音识别和语音识别的两个变量是否开启
        while self.__running.isSet ():  
            self.__flag.wait ()                 # 这句话与__flag变量相关。当它为True时, 会正常执行。为False时会一直卡在这里, 直到为True
            connect_identify = Connect_identify()
            connect_identify.start()
            time.sleep ( 1 )

    # 需要让线程暂停
    def pause(self):
        self.__flag.clear ()                    # 设置为False, 让线程暂停
    # 需要让线程继续
    def resume(self):
        self.__flag.set ()                      # 设置为True, 让线程继续
    # 需要让线程停止
    def stop(self):
        self.__flag.set ()                      # 将线程从暂停状态恢复。
        self.__running.clear ()                 # 设置为False, 停止线程


# 2.开启新线程去做语音识别整过程

# 根据话题控制启动、暂停、停止
def callback(data):
    global voice_thread # 控制语音线程启动和停止
    global duplicate_removal
    global thread_rec

    # 订阅去重
    if duplicate_removal == data.data:
        return
    duplicate_removal = data.data

    # 如果大于0就开启语音识别
    if int ( data.data ) > 0:  # 根据传入的数字决定是否开启 
        # rospy.loginfo('请继续讲话')
        # 如果条件都满足就启动语音识别(语音、线程、重置)
        try:
            # 开一个子线程用于识别 (录制、连接、发送等) , 主线程继续订阅ros消息
            voice_thread = True
            thread_rec = Job ()                 # 创建一个线程对象 (调用两次就是两个线程) 
            thread_rec.resume()                 # 继续线程。防止暂停了线程
            thread_rec.start ()                 # 开启线程 (调用里面的run方法) 
            print ( "- - - - - - - 请讲话 - - - - - - - " )
        except Exception as e:
            print ( e )

    # 等于0停止
    elif int ( data.data ) == 0:
        # rospy.loginfo('停止语音识别')
        thread_rec.pause()                     # 关掉整个语音线程
        voice_thread = False                   # 关掉语音识别线程

    # 小于0就退出
    else:
        # 关闭语音识别
        voice_thread = False
        thread_rec.pause()                     # 关掉整个语音线程
        rospy.loginfo('传过来的信息小于或等于0, 退出节点')
        # 通知 ROS 关闭这个节点
        rospy.signal_shutdown('退出节点')

# 1.订阅tts消息

def main():
    global publisher_thread, publisher_stop, identify_stop, identify_thread
    global voice_thread, duplicate_removal, thread_rec
    global session_data, scenario, session

    # 线程变量
    #   识别结果发布线程
    publisher_thread = None  # 线程对象
    publisher_stop = threading.Event()               # 实例化threading.Event对象。用于控制线程开关
    #   识别线程
    identify_thread = None
    identify_stop = threading.Event()

    # 其他变量
    voice_thread = False                             # 语音识别是否开启标志符

    duplicate_removal = None                         # 语音去重
    thread_rec = None                                # 整个语音识别线程控制

    # 创建全局会话对象，复用连接
    session = requests.Session()
    session.trust_env = False                        # 不读取系统/环境变量代理

    # 全局会话数据，用于维护对话上下文
    session_data = {
        "conversation_id": None,
        "parent_message_id": "client-created-root",  # 初始根消息ID
        "last_message_id": None
    }

    # 给GPT的情景说明文本
    scenario = ("你是ai语音助手, 我现在要将你集成到我的ros小车机器人上面供用户用语音调用, 用户的输入有两类, "
                "一类是闲聊式, 一类是命令式 (驱动机器人) 。你在接收到输入时, 首先对输入就行常规语法纠正 (语音识别有可能识别不准) ,"
                "然后判断输入类型，如果是简单的问题，我需要你快速响应，涉及比较难的问题可以适当延长思考时间。"
                "1.闲聊："
                "用户有时候会输入一些命令之外的内容, 你的回答需简明扼要。注：无需指明是什么类型的问题，直接回复即可"
                "2.命令式 (驱动机器人) ："
                "现在我给用户的控制内容就只有导航和前后左右走, 因此只有这两类才属于命令式 (驱动机器人) 。"
                "对于导航的你直接回复 '导航点几（数字）'数字，对于前后左后，需要回复单个方位词（前) "
                "其他任何东西都不能回复。\n 我要问的第一个问题是：")       


    global pub
    rospy.init_node('voice_asr')

    # 创建发布者对象, 将识别到的语音发布给语音合成节点
    pub = rospy.Publisher('asr_result', String, queue_size=10)

    # 创建订阅者对象。订阅语音合成节点发布过来的开启或关闭语音识别命令
    rospy.Subscriber ( "voice_asr", String, callback)

    rospy.spin ()


if __name__ == '__main__':

    # 进行调用
    main()  
