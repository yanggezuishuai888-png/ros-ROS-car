
#include <Arduino.h>
/*
  1.大致说明：
    这个程序就是整个底层的主入口，他将编码器脉冲计数、电机驱动、PID、命令等
    全部继承到这个文件了。这里主要是写了一个串口读取函数，然后根据读取到的值
    执行对应命令。这里设置了大量的宏，决定是否启用编码器脉冲计数等功能。如果
    需要扩展，就在这里写宏，然后在别的文件写实现即可

  2.具体逻辑：
    setup中做初始化。loop中刚开始就一直读取串口的值，一个字符一个字符读，然
    后分析，等到读到“\r”（回车符）时终止，开始分析读到的内容执行对应命令。并且
    PID是肯定会调试的
  
  3.执行顺序：
    首先会循环读取串口信息，并且会持续更新PID，当然如果不驱动轮子，更新也没有用。
    如果读到e就会调用脉冲计数（encoder_driver.ino）里面的函数获取脉冲数；如
    果读到m首先会调用diff_contoller.h进行PID计算，算出pwm，然后进行调用
    motor_dribver.ino里面的驱动函数
  4.注意：
    结合ros之后要将电机运行时间调成5s
*/


void softwareReset()
{
  Serial.println("Software reset...");
  delay(50);          // 让串口把字发完
  NVIC_SystemReset(); // ★ 真·软件复位
  while (1);          // 永远执行不到
}

// -------------------------------------- 驱动、编码器等宏开关 -------------------------------------
// 是否启动基控制器，是否使用这个包（后期需要启动）
#define USE_BASE   
//#undef USE_BASE  

// 编码器和电机驱动相关实现
#ifdef USE_BASE

  // 自定义编码器驱动
  #define ARDUINO_MY_COUNTER

  // 自定义电机驱动
  #define TB6612_MOTOR_DRIVER


#endif
// -------------------------------------- 驱动、编码器等宏开关 -------------------------------------

// 波特率
// #define BAUDRATE     57600
#define BAUDRATE 115200

// PWM最大值
#define MAX_PWM        255

// 导入arduino底层文件（兼容不同版本）
#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

// 串口通信命令
#include "commands.h"

// 超声波、红外等传感器启动函数
#include "sensors.h"

// #define TEST

// -------------------------------------- 电机驱动相关头文件导入 -------------------------------------
#ifdef USE_BASE
  // 电机驱动
  #include "motor_driver.h"

  // 编码器驱动
  #include "encoder_driver.h"

  // 差速控制器（PID控制）
  #include "diff_controller.h"

  // PID控制 ---- 调试频率。即每秒更新30次。
  #define PID_RATE           30

  // PID控制 ---- 调试周期。因为millis返回的时间单位是ms，频率时s，因此这里将单位统一转成ms
  const int PID_INTERVAL = 1000 / PID_RATE;
  
  // PID控制 ---- 执行下一次PID控制的时间点（时间戳）。每执行完一次PID会加一各周期
  unsigned long nextPID = PID_INTERVAL;

  // 电机接受到速度指令后的运行时间。结合ros之后要调成5s
  #define AUTO_STOP_INTERVAL 5000
  long lastMotorCommand = AUTO_STOP_INTERVAL;
#endif

// -------------------------------------- 电机驱动相关头文件导入 -------------------------------------

// 参数位置索引
int arg = 0;

// argv1/2数组位置索引
int arg_index = 0;

// 存储读取字符
char chr;

// 存储命令字符变量（m、r等）
char cmd;

// 存储数值的值。比如：m 100 100.argv1存储第一个‘1’、‘0’、‘0’，argv2存储第二个‘1’、‘0’、‘0’
char argv1[16];
char argv2[16];
char argv3[16];
char argv4[16];

// 存储类型转换后的参数1、参数2变量
long arg1;
long arg2;
long arg3;
long arg4;

// 将读取命令相关参数清零
void resetCommand() 
{
  cmd = NULL;
  memset(argv1, 0, sizeof(argv1));
  memset(argv2, 0, sizeof(argv2));
  memset(argv3, 0, sizeof(argv3));   
  memset(argv4, 0, sizeof(argv4));   
  arg1 = 0;
  arg2 = 0;
  arg3 = 0;
  arg4 = 0;
  arg = 0;
  arg_index = 0;
}
// 将读取命令相关参数清零 



// 处理（运行）命令
int runCommand() 
{
  
  // char *p = argv1;
  // char *str;
  int i = 0;           // PID - 提取参数的顺序 
  char *p_local;       // PID - 分别存储argv1、2、3、4
  char *token;         // PID - 存储提取出来的字符串
  int pid_args[4];     // PID - PID增益存储数组
  arg1 = atoi(argv1);  // 将数值转成整数.系统
  arg2 = atoi(argv2);
  arg3 = atoi(argv3);  
  arg4 = atoi(argv4);

  #ifdef TEST
  Serial.print("arg1 arg2 arg3 arg4 ----- ");
  Serial.print(arg1);
  Serial.print(arg2);
  Serial.print(arg3);
  Serial.println(arg4);
  #endif
  switch(cmd) 
  {
  
  case GET_BAUDRATE:      // b ----- 打印波特率
    Serial.println(BAUDRATE);
    break;
  case ANALOG_READ:       // a ----- 读第一个参数的模拟口值并打印
    Serial.println(analogRead(arg1));
    break;
  case DIGITAL_READ:      // d ----- 读第一个参数的数字引脚值并打印
    Serial.println(digitalRead(arg1));
    break;
  case ANALOG_WRITE:      // x
    analogWrite(arg1, arg2);
    Serial.println("OK"); 
    break;
  case DIGITAL_WRITE:     // w ---- 给arg1引脚 设置高、低电平
    if (arg2 == 0) digitalWrite(arg1, LOW);
    else if (arg2 == 1) digitalWrite(arg1, HIGH);
    Serial.println("OK"); 
    break;
  case PIN_MODE:          // c
    if (arg2 == 0) pinMode(arg1, INPUT);
    else if (arg2 == 1) pinMode(arg1, OUTPUT);
    Serial.println("OK");
    break;
  case PING:              // p
    Serial.println(Ping(arg1));
    break;
  // 电机驱动等相关
#ifdef USE_BASE
  case READ_ENCODERS:     // e ---- 打印左右编码器脉冲
    Serial.print(readEncoder(FRONT_LEFT));
    Serial.print(" ");
    Serial.print(readEncoder(FRONT_RIGHT));
    Serial.print(" ");
    Serial.print(readEncoder(AFTER_LEFT));
    Serial.print(" ");
    Serial.println(readEncoder(AFTER_RIGHT));
    break;
   case RESET_ENCODERS:   // r ---- 清零左右编码器脉冲 PID内部状态也清零
    resetEncoders();
    resetPID();
    Serial.println("OK");
    break;
  case MOTOR_SPEEDS:      // m ---- 设置左右电机转速
    lastMotorCommand = millis();

    if (arg1 == 0 && arg2 == 0 && arg3 == 0 && arg4 == 0) 
    {
      setMotorSpeeds(0, 0, 0, 0);
      resetPID();
      moving = 0;
    }

    else moving = 1;
    // 设置PID调试的目标值（拿到输入参数）
    FRONT_LEFT_PID.TargetTicksPerFrame = arg1 + 1;
    FRONT_RIGHT_PID.TargetTicksPerFrame = arg2;
    AFTER_LEFT_PID.TargetTicksPerFrame = arg3 + 1;
    AFTER_RIGHT_PID.TargetTicksPerFrame = arg4;
    Serial.println("OK"); 
    break;
  case UPDATE_PID:  // u ---- 设置PID。例如：u 20:12:0:50\r

    // // 将字符串按照“：”拆分
    // while ((str = strtok_r(p, ":", &p)) != NULL) 
    // {
    //    pid_args[i] = atoi(str);
    //    i++;
    // }
    // FRONT_LEFT_PID.Kp = pid_args[0];
    // FRONT_LEFT_PID.Kd = pid_args[1];
    // FRONT_LEFT_PID.Ki = pid_args[2];
    // FRONT_LEFT_PID.Ko = pid_args[3];
    // Serial.println("OK");
    // break;

    // ---------- 前左轮 FRONT_LEFT_PID ----------
    p_local = argv1;

    while ((token = strtok_r(p_local, ":", &p_local)) != NULL && i < 4) 
    {
      pid_args[i++] = atoi(token);
    }

    if (i == 4) {
      FRONT_LEFT_PID.Kp = pid_args[0];
      FRONT_LEFT_PID.Kd = pid_args[1];
      FRONT_LEFT_PID.Ki = pid_args[2];
      FRONT_LEFT_PID.Ko = pid_args[3];
    }

    // ---------- 前右轮 FRONT_RIGHT_PID ----------
    p_local = argv2;
    i = 0;
    while ((token = strtok_r(p_local, ":", &p_local)) != NULL && i < 4) {
      pid_args[i++] = atoi(token);
    }
    if (i == 4) {
      FRONT_RIGHT_PID.Kp = pid_args[0];
      FRONT_RIGHT_PID.Kd = pid_args[1];
      FRONT_RIGHT_PID.Ki = pid_args[2];
      FRONT_RIGHT_PID.Ko = pid_args[3];
    }

    // ---------- 后左轮 AFTER_LEFT_PID ----------
    p_local = argv3;
    i = 0;
    while ((token = strtok_r(p_local, ":", &p_local)) != NULL && i < 4) {
      pid_args[i++] = atoi(token);
    }
    if (i == 4) {
      AFTER_LEFT_PID.Kp = pid_args[0];
      AFTER_LEFT_PID.Kd = pid_args[1];
      AFTER_LEFT_PID.Ki = pid_args[2];
      AFTER_LEFT_PID.Ko = pid_args[3];
    }

    // ---------- 后右轮 AFTER_RIGHT_PID ----------
    p_local = argv4;
    i = 0;
    while ((token = strtok_r(p_local, ":", &p_local)) != NULL && i < 4) {
      pid_args[i++] = atoi(token);
    }
    if (i == 4) {
      AFTER_RIGHT_PID.Kp = pid_args[0];
      AFTER_RIGHT_PID.Kd = pid_args[1];
      AFTER_RIGHT_PID.Ki = pid_args[2];
      AFTER_RIGHT_PID.Ko = pid_args[3];
    }

    Serial.println("OK");
    break;
  case 'z':
    softwareReset();
    break;
#endif
  default:
    Serial.println("Invalid Command");
    break;
  }
}


void setup() 
{
  Serial.begin(BAUDRATE);
  pinMode(LED_BUILTIN, OUTPUT);   // 开13号灯
#ifdef USE_BASE
  // 自己写的编码器驱动初始化
  #ifdef ARDUINO_MY_COUNTER
    // 调用初始化函数
    initEncoder();

  #endif
  #ifdef TB6612_MOTOR_DRIVER
    // 电机驱动初始化
    initMotorController();
  #endif
  // PID等其他置零
  resetPID();
  // 重新对PID初始化
  initPID();
#endif
}


void loop() 
{
  // ------------------------------------- 读取串口参数 -------------------------------------
  /*
  1.作用：
    获取串口参数，并调用函数对参数进行解释、执行
  
  3.原理：
    通过Serial.read持续读取串口中的值，这个函数是一个一个值读取的，
    然后对空格的识别来，结合arg位置索引，判断读取参数的位置
  
  */
  // 开13号灯
  // digitalWrite(LED_BUILTIN, HIGH);  
  while (Serial.available() > 0) 
  {

    
    // 读取串口信息
    chr = Serial.read();

    // 当串口终止符是CR（回车），表示命令输入完成，开始命令的执行
    if (chr == 13) 
    {
      // 只输入一个字符命令
      if (arg == 1) argv1[arg_index] = NULL;
      // 输入一个字符命令加一个数值（控制一个电机）
      else if (arg == 2) argv2[arg_index] = NULL;
      else if (arg == 3) argv3[arg_index] = NULL;   
      else if (arg == 4) argv4[arg_index] = NULL;   
      runCommand();
      resetCommand();
    }
    
    // 通过空格来切换读取的槽位
    else if (chr == ' ') {
      // 第一次读到空格（命令字符后面的空格）
      if (arg == 0)
      {
        arg = 1;  // 将arg赋值为1,表示现在已经读完1了
      }
      // 第二次读到空格，第一个数值后面的空格。
      else if (arg == 1)  
      {
        argv1[arg_index] = NULL;  // 给第一个数组添加一个‘\0’字符，表示第一个参数已经读完
        arg = 2; // 将arg赋值为2,表示现在已经读完2了
        arg_index = 0;  // 重新将arg_index赋为0,用来做第二个参数的索引。
      }
      else if (arg == 2) 
      {
      argv2[arg_index] = NULL;     
      arg = 3;                      
      arg_index = 0;
      }
      else if (arg == 3) 
      {
      argv3[arg_index] = NULL;      
      arg = 4;                      
      arg_index = 0;
      }

      continue;
    }

    // 既不是回车，也不是空格，那就是命令字符（m、r等）、输入值
    else {
      if (arg == 0) 
      {
        // 命令字符赋值
        cmd = chr;
      }
      else if (arg == 1) 
      {
        
        argv1[arg_index] = chr;
        arg_index++;  // 将数组索引加1,方便下一个存储
      }
      else if (arg == 2) 
      {
        argv2[arg_index] = chr;
        arg_index++;
      }
      else if (arg == 3) 
      {
        argv3[arg_index] = chr;
        arg_index++;  
      } 
      else if (arg == 4) 
      {
        argv4[arg_index] = chr;
        arg_index++;  
      }

    }
  }
  // ------------------------------------- 读取串口参数 -------------------------------------
  
// -------------------------------------- PID调用 -------------------------------------
#ifdef USE_BASE
  // 判断时间是否够一个周期（millis()是从程序刚执行setup开始算的）
  if (millis() > nextPID) 
  {
    updatePID();  // 循环更新PID
    nextPID += PID_INTERVAL;  // 更新一个周期
  }
  
  // 判断电机执行时间，将其运行规定在指定的时间内
  if ((millis() - lastMotorCommand) > AUTO_STOP_INTERVAL) 
  {
    setMotorSpeeds(0, 0, 0, 0);
    moving = 0;
  }
#endif

// -------------------------------------- PID调用 -------------------------------------

}
