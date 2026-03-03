/***************************************************************
  1.说明：
    这个代码时电机驱动代码。就是一个命令输入电机速度，然后先调用PID算出真正的pwm，接着给pwm给电机让他转动（注：PID计算在‘diff_controller.h
    所以改他时，需要先改PID部分）
    
  2.具体逻辑：
    写一个单电机控制函数，让电机动的。接收两个参数，LEFT/RIGHT 转速
    然后再写一个函数，接收两个参数，分别是两电机转速，然后在里面调用两次单电机即可。最后运行时就输入m 100 100
    后面两个转速就会自动传给该函数，并且有延时。
  
  3.实现步骤：
    3-1.增加引脚
    3-2.在单电机转速那添加另外领个轮子代码
    3-3.在两个电机调用那添加多两个调用
  4.注意：
    没调好PID时，直接给速度（m 100 100），所显示的方向没有什么参考价值，因为PID不对，参考方向会随时变
*************************************************************/

#ifdef USE_BASE
   
// ---------------------------------- 整个文件：不同驱动板的电机驱动代码实现 ----------------------------------
#ifdef TB6612_MOTOR_DRIVER
  // 1.初始化
  void initMotorController()
  {
    // pinMode(FRONT_LEFT_CN2, OUTPUT);
    // pinMode(FRONT_LEFT_CN1, OUTPUT);
    // pinMode(FRONT_RIGHT_BN2, OUTPUT);
    // pinMode(FRONT_RIGHT_BN1, OUTPUT);
    // pinMode(AFTER_LEFT_DN2, OUTPUT);
    // pinMode(AFTER_LEFT_DN1, OUTPUT);
    // pinMode(AFTER_RIGHT_AN2, OUTPUT);
    // pinMode(AFTER_RIGHT_AN1, OUTPUT);
    // 先设置所有控制方向的引脚为 OUTPUT 并写 LOW
    pinMode(FRONT_LEFT_CN2, OUTPUT);  digitalWrite(FRONT_LEFT_CN2, LOW);
    pinMode(FRONT_LEFT_CN1, OUTPUT);  digitalWrite(FRONT_LEFT_CN1, LOW);

    pinMode(FRONT_RIGHT_BN2, OUTPUT); digitalWrite(FRONT_RIGHT_BN2, LOW);
    pinMode(FRONT_RIGHT_BN1, OUTPUT); digitalWrite(FRONT_RIGHT_BN1, LOW);

    pinMode(AFTER_LEFT_DN2, OUTPUT);  digitalWrite(AFTER_LEFT_DN2, LOW);
    pinMode(AFTER_LEFT_DN1, OUTPUT);  digitalWrite(AFTER_LEFT_DN1, LOW);

    pinMode(AFTER_RIGHT_AN2, OUTPUT); digitalWrite(AFTER_RIGHT_AN2, LOW);
    pinMode(AFTER_RIGHT_AN1, OUTPUT); digitalWrite(AFTER_RIGHT_AN1, LOW);

    pinMode(STBY, OUTPUT);

    digitalWrite(STBY, 1);
  }  

  // 2.设置单个电机转速(i：左、右 spd：速度)
  void setMotorSpeed(int i, int spd)
  {
    unsigned char reverse = 0;  // 正反转布尔值

    // 2-1.速度值判断(决定转反转)
    if (spd < 0)
    {
      spd = -spd;
      reverse = 1;  
    }
    if (spd > 255)
    {
      spd = 255;
    }
    // 2-2.驱动前左轮(C)
    if (i == FRONT_LEFT)
    { 
      // 正转
      if (reverse == 0)
      { 
        digitalWrite(FRONT_LEFT_CN2, HIGH);
        digitalWrite(FRONT_LEFT_CN1, LOW);
      }
      // 反转
      else if (reverse == 1)
      { 
        digitalWrite(FRONT_LEFT_CN2, LOW);
        digitalWrite(FRONT_LEFT_CN1, HIGH); 
      }
      // 左轮转速
      analogWrite(FRONT_LEFT_PWMC, spd);
    }
    // 2-3.驱动前右轮(B)
    else if (i == FRONT_RIGHT)
    {
      // 正转
      if (reverse == 0)
      { 
        digitalWrite(FRONT_RIGHT_BN2, LOW);
        digitalWrite(FRONT_RIGHT_BN1, HIGH);   
      }
      // 反转
      else if (reverse == 1)
      { 
        digitalWrite(FRONT_RIGHT_BN2, HIGH);
        digitalWrite(FRONT_RIGHT_BN1, LOW);
      }
      // 左轮转速
      analogWrite(FRONT_RIGHT_PWMB, spd);
    }
    // 2-4.驱动后左轮(D)
    else if (i == AFTER_LEFT)
    {
      // 正转
      if (reverse == 0)
       { 
        digitalWrite(AFTER_LEFT_DN2, LOW);
        digitalWrite(AFTER_LEFT_DN1, HIGH);
       }
      
      // 反转
      else if (reverse == 1) 
      { 
        digitalWrite(AFTER_LEFT_DN2, HIGH);
        digitalWrite(AFTER_LEFT_DN1, LOW); 
      }
      // 右轮转速
      analogWrite(AFTER_LEFT_PWMD, spd);
    }
    // 2-5.驱动后右轮(A)
    else if (i == AFTER_RIGHT)
    {
      // 正转
      if (reverse == 0)
       { 
        // digitalWrite(AFTER_RIGHT_AN2, LOW);
        // digitalWrite(AFTER_RIGHT_AN1, HIGH);
        digitalWrite(AFTER_RIGHT_AN2, HIGH);
        digitalWrite(AFTER_RIGHT_AN1, LOW); 
       }
      
      // 反转
      else if (reverse == 1) 
      { 
        // digitalWrite(AFTER_RIGHT_AN2, HIGH);
        // digitalWrite(AFTER_RIGHT_AN1, LOW); 
        digitalWrite(AFTER_RIGHT_AN2, LOW);
        digitalWrite(AFTER_RIGHT_AN1, HIGH);
      }
      // 右轮转速
      analogWrite(AFTER_RIGHT_PWMA, spd);
    }
  }

  // 3.设置四个电机转速(调用四次单电机)。PID那边调用的
  void setMotorSpeeds(int front_left_Speed, int front_right_Speed, int arter_left_Speed, int arter_right_Speed)
  {
    setMotorSpeed(FRONT_LEFT, front_left_Speed);
    setMotorSpeed(FRONT_RIGHT, front_right_Speed);
    setMotorSpeed(AFTER_LEFT, arter_left_Speed);
    setMotorSpeed(AFTER_RIGHT, arter_right_Speed);
  }

#else
  #error A motor driver must be selected!
#endif

#endif
