/*
  说明：
    编码器脉冲计数函数头文件
*/
   

// 自己的编码器驱动 
#ifdef ARDUINO_MY_COUNTER
  // 定义编码器输出引脚（FRONT_LEFT、FRONT_RIGHT、AFTER_LEFT、AFTER_RIGHT，命名规则：位置_对应驱动板上接口名称）
  #define FRONT_LEFT_E3A 33
  #define FRONT_LEFT_E3B 34

  #define FRONT_RIGHT_E2A 37
  #define FRONT_RIGHT_E2B 38
  
  #define AFTER_LEFT_E4A 41
  #define AFTER_LEFT_E4B 42
  
  #define AFTER_RIGHT_E1A 45
  #define AFTER_RIGHT_E1B 46

  
  
  // 声明函数
  //1.初始化函数：设置引脚操作模式，并添加中断
  void initEncoder();
  //2.中断函数
  // 3-1.前左（FRONT_LEFT）：
  void FRONT_LEFT_CA();
  // 3-2.前左（FRONT_LEFT）：
  void FRONT_LEFT_CB();
  // 3-3.前右（FRONT_RIGHT）：
  void FRONT_RIGHT_BA();
  // 3-4.前右（FRONT_RIGHT）：
  void FRONT_RIGHT_BB();
  // 3-5.后左（AFTER_LEFT）：
  void AFTER_LEFT_DA();
  // 3-6.后左（AFTER_LEFT）：
  void AFTER_LEFT_DB();
  // 3-7.后右（AFTER_RIGHT）：
  void AFTER_RIGHT_AA();
  // 3-8.后右（AFTER_RIGHT）：
  void AFTER_RIGHT_AB();
#endif
   
// 读单个电机编码器计数
long readEncoder(int i);

// 重置单个电机的计数器
void resetEncoder(int i);

// 重置四个轮的计数器
void resetEncoders();

