/***************************************************************
   Motor driver function definitions - by James Nugen
   *************************************************************/

#ifdef TB6612_MOTOR_DRIVER
  // 定义左右电机使用的引脚（命名规则：电机位置_驱动板上对应实际接口名）
  #define STBY 30 // 电机总控制
  #define FRONT_LEFT_PWMC 5
  #define FRONT_LEFT_CN2 31
  #define FRONT_LEFT_CN1 32

  #define FRONT_RIGHT_PWMB 4
  #define FRONT_RIGHT_BN2 35
  #define FRONT_RIGHT_BN1 36

  #define AFTER_LEFT_PWMD 3
  #define AFTER_LEFT_DN2 39
  #define AFTER_LEFT_DN1 40

  #define AFTER_RIGHT_PWMA 2
  #define AFTER_RIGHT_AN2 43
  #define AFTER_RIGHT_AN1 44

#endif

void initMotorController();  // 初始化
void setMotorSpeed(int i, int spd);  // 设置单个电机速度
void setMotorSpeeds(int front_left_Speed, int front_right_Speed, int arter_left_Speed, int arter_right_Speed);  // 设置两个电机速度
