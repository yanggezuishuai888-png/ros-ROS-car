/*
  1.说明：
    这个是纯自己计算的PID，没有调用任何库
    注：脉冲数又叫tick
  2.具体逻辑：
    （1）给每个轮子都实例化一个结构体
    （2）定义PID的跳转函数，让每个轮子都能单独调参
    （3）主入口那边设置周期，每个周期都会调用updaPID函数
    （4）调用doPID函数计算pwm
    （5）调用电机驱动的setMotorSpeeds驱动电机
  3.PID算法逻辑（doPID）：
    m指定速度并非真实速度，而是tick值，整个PID都是围绕tick来展开的
    （实际速度比目标值小1/2左右）
    首先ROSArduinobridge会指定目标值（每个周期需要达到的tick值），
    接着计算每个周期计算一次tick值（当前周期走的tick）和与目标tick
    的误差再通过指定算法计算当前周期应该输出pwm
  4.注意：
  （1）结合ros时，要注释掉输出（printf），否则会数据错误
  （2）改完后需要将ROSArduinoBridge.ino电机运行时间改回5s
  （3）改PID前需要先改编码器部分
*/

// 结构体定义。里面是可公用的PID相关参数
typedef struct 
{
  double TargetTicksPerFrame;    // 目标值
  long Encoder;                  // 当前编码器计数
  long PrevEnc;                  // 上一次调试结束时累计的编码器计数
  int PrevInput;                 // 上一次计算时的速度输入
  double ITerm;                     // 积分项累计值 = ITerm + Ki * error
  long output;                   // 计算好的PWM波
  // PID
  double Kp = 5;
  double Ki = 0.5;
  double Kd = 2;
  double Ko = 50;               // 对PID影响不大
} SetPointInfo;

// 类似实例化
SetPointInfo FRONT_LEFT_PID, FRONT_RIGHT_PID, AFTER_LEFT_PID, AFTER_RIGHT_PID;

// PID初始化（调参）。在主入口的setup中调用
void initPID() 
{
  // 左前轮
  FRONT_LEFT_PID.Kp = 7.0;
  FRONT_LEFT_PID.Ki = 0.4;
  FRONT_LEFT_PID.Kd = 1.0;
  FRONT_LEFT_PID.Ko = 50.0;

  // 右前轮
  FRONT_RIGHT_PID.Kp = 6.5;
  FRONT_RIGHT_PID.Ki = 0.2;
  FRONT_RIGHT_PID.Kd = 0.1;
  FRONT_RIGHT_PID.Ko = 50.0;

  // 左后轮
  AFTER_LEFT_PID.Kp = 6.0;
  AFTER_LEFT_PID.Ki = 0.3;
  AFTER_LEFT_PID.Kd = 0.5;
  AFTER_LEFT_PID.Ko = 50.0;


  // 右后轮
  AFTER_RIGHT_PID.Kp = 7.0;
  AFTER_RIGHT_PID.Ki = 0.2;
  AFTER_RIGHT_PID.Kd = 0.1;
  AFTER_RIGHT_PID.Ko = 50.0;
}

unsigned char moving = 0; 

// PID参数置零
void resetPID()
{
  // 前左轮PID相关数据
  FRONT_LEFT_PID.TargetTicksPerFrame = 0.0;
  // FRONT_LEFT_PID.Encoder = readEncoder(LEFT);
  FRONT_LEFT_PID.Encoder = readEncoder(FRONT_LEFT);
  FRONT_LEFT_PID.PrevEnc = FRONT_LEFT_PID.Encoder;
  FRONT_LEFT_PID.output = 0;
  FRONT_LEFT_PID.PrevInput = 0;
  FRONT_LEFT_PID.ITerm = 0;

  // 前右轮PID相关数据
  FRONT_RIGHT_PID.TargetTicksPerFrame = 0.0;
  // FRONT_RIGHT_PID.Encoder = readEncoder(RIGHT);
  FRONT_RIGHT_PID.Encoder = readEncoder(FRONT_RIGHT);
  FRONT_RIGHT_PID.PrevEnc = FRONT_RIGHT_PID.Encoder;
  FRONT_RIGHT_PID.output = 0;
  FRONT_RIGHT_PID.PrevInput = 0;
  FRONT_RIGHT_PID.ITerm = 0;

  // 后左轮PID相关数据
  AFTER_LEFT_PID.TargetTicksPerFrame = 0.0;
  // AFTER_LEFT_PID.Encoder = readEncoder(LEFT);
  AFTER_LEFT_PID.Encoder = readEncoder(AFTER_LEFT);
  AFTER_LEFT_PID.PrevEnc = AFTER_LEFT_PID.Encoder;
  AFTER_LEFT_PID.output = 0;
  AFTER_LEFT_PID.PrevInput = 0;
  AFTER_LEFT_PID.ITerm = 0;

  // 后右轮PID相关数据
  AFTER_RIGHT_PID.TargetTicksPerFrame = 0.0;
  // AFTER_RIGHT_PID.Encoder = readEncoder(RIGHT);
  AFTER_RIGHT_PID.Encoder = readEncoder(AFTER_RIGHT);
  AFTER_RIGHT_PID.PrevEnc = AFTER_RIGHT_PID.Encoder;
  AFTER_RIGHT_PID.output = 0;
  AFTER_RIGHT_PID.PrevInput = 0;
  AFTER_RIGHT_PID.ITerm = 0;
}

void doPID(SetPointInfo * p) {
  long Perror;
  long output;
  int input;

  // p->Encoder表示访问结构体里面的变量

  // 当前周期内变化的tick
  input = p->Encoder - p->PrevEnc;

  // 误差 = 目标值（每个周期内需达到的tick值） - 当前周期达到的tick值
  Perror = p->TargetTicksPerFrame - input;

  // 计算pwm,相对于上一个周期应该加/减多少
  output = (p->Kp * Perror - p->Kd * (input - p->PrevInput) + p->ITerm) / p->Ko;
  
  // 更新上一次个周期的脉冲数
  p->PrevEnc = p->Encoder;

  // 累加输出（上一次pwm）
  output += p->output;

  // 防止溢出（-255 到 255）
  if (output >= MAX_PWM)
    output = MAX_PWM;
  else if (output <= -MAX_PWM)
    output = -MAX_PWM;
  else

  // 抗饱和积分
  p->ITerm += p->Ki * Perror;

  // 输出
  p->output = output;
  p->PrevInput = input;
  
  // 当前速度（脉冲，其实就相当于速度）。结合ros时，要注释掉，否则会数据错误
  // Serial.println(input);
  // Serial.println(output);
}

// 更新PID函数
void updatePID() {
  
  // 获取当前编码器计数
  FRONT_LEFT_PID.Encoder = readEncoder(FRONT_LEFT); 
  FRONT_RIGHT_PID.Encoder = readEncoder(FRONT_RIGHT);
  AFTER_LEFT_PID.Encoder = readEncoder(AFTER_LEFT); 
  AFTER_RIGHT_PID.Encoder = readEncoder(AFTER_RIGHT);

  // moving为0
  if (!moving){
    if (FRONT_LEFT_PID.PrevInput != 0 || FRONT_RIGHT_PID.PrevInput != 0 ||
        AFTER_LEFT_PID.PrevInput != 0 || AFTER_RIGHT_PID.PrevInput != 0) resetPID();
    return;
  }

  // 调用
  doPID(&FRONT_LEFT_PID);
  doPID(&FRONT_RIGHT_PID);
  doPID(&AFTER_LEFT_PID);
  doPID(&AFTER_RIGHT_PID);

  // 调用电机驱动函数，将pwm给到电机
  setMotorSpeeds(FRONT_LEFT_PID.output, FRONT_RIGHT_PID.output, 
                AFTER_LEFT_PID.output, AFTER_RIGHT_PID.output);
}

