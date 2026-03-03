/* *************************************************************
  1.说明：
    这个文件是编码器脉冲计数，是主入口中根据命令调用的，包括获取四个轮子的编码器脉冲数，
    将四个编码器脉冲置零这两个命令。具体的编码器脉冲计数函数也是在这里实现
  2.具体逻辑：
    ·定义引脚、初始化
    ·给四个轮子写8个中断函数（一个编码器两个）用来计数
    ·读取串口命令函数实现
    ·获取脉冲数、置零脉冲数函数实现
   
************************************************************ */
   
#ifdef USE_BASE

// 如果定义了编码器宏，就执行这个驱动
#ifdef ARDUINO_MY_COUNTER

  // 1.定义计数器
  volatile long FRONT_LEFT_count = 0L;
  volatile long FRONT_RIGHT_count = 0L;
  volatile long AFTER_LEFT_count = 0L;
  volatile long AFTER_RIGHT_count = 0L;

  // 2.初始化
  void initEncoder() 
  {

    pinMode(FRONT_LEFT_E3A, INPUT);
    pinMode(FRONT_LEFT_E3B, INPUT);
    pinMode(FRONT_RIGHT_E2A, INPUT);
    pinMode(FRONT_RIGHT_E2B, INPUT);

    pinMode(AFTER_LEFT_E4A, INPUT);
    pinMode(AFTER_LEFT_E4B, INPUT);
    pinMode(AFTER_RIGHT_E1A, INPUT);
    pinMode(AFTER_RIGHT_E1B, INPUT);

    // 添加中断
    attachInterrupt(digitalPinToInterrupt(FRONT_LEFT_E3A), FRONT_LEFT_CA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(FRONT_LEFT_E3B), FRONT_LEFT_CB, CHANGE);

    attachInterrupt(digitalPinToInterrupt(FRONT_RIGHT_E2A), FRONT_RIGHT_BA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(FRONT_RIGHT_E2B), FRONT_RIGHT_BB, CHANGE);

    attachInterrupt(digitalPinToInterrupt(AFTER_LEFT_E4A), AFTER_LEFT_DA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(AFTER_LEFT_E4B), AFTER_LEFT_DB, CHANGE);

    attachInterrupt(digitalPinToInterrupt(AFTER_RIGHT_E1A), AFTER_RIGHT_AA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(AFTER_RIGHT_E1B), AFTER_RIGHT_AB, CHANGE);
  }
  

  // 3.编写中断回调函数(命名：轮位置_对应驱动字母 驱动脉冲符号【A B】)
  // 3-1.前左（FRONT_LEFT）- A波：A高-B高为正：
  void FRONT_LEFT_CA()
  {
    // 当A跳转到高电平
    if(digitalRead(FRONT_LEFT_E3A) == HIGH)
    {
      // B高电压 - 正转
      if (digitalRead(FRONT_LEFT_E3B) == HIGH)
      {
          FRONT_LEFT_count ++;
      }
      // B低电压 - 反转
      else
      {
        FRONT_LEFT_count --;
      }
    }
    
    // A跳变到低电平
    else
    {
      // B低电压 - 正转
      if (digitalRead(FRONT_LEFT_E3B) == LOW)
      {
        FRONT_LEFT_count ++;
      }
      // B高电压 - 反转
      else
      {
        FRONT_LEFT_count --;
      }
    }
  }

  // 3-2.前左（FRONT_LEFT）- B波：B高-A低为正
  void FRONT_LEFT_CB()
  {
    // 当B跳变为上升沿
    if(digitalRead(FRONT_LEFT_E3B) == HIGH)
    {
      // A低电压 - 正转
      if (digitalRead(FRONT_LEFT_E3A) == LOW)
      {
          FRONT_LEFT_count ++;
      }
      // A高电压 - 反转
      else
      {
        FRONT_LEFT_count --;
      }
    }
    
    // B跳变到低电平
    else
    {
      // A高电压 - 正转
      if (digitalRead(FRONT_LEFT_E3A) == HIGH)
      {
        FRONT_LEFT_count ++;
      }
      // A低电压 - 反转
      else
      {
        FRONT_LEFT_count --;
      }
    }
  }

  // 3-3.前右（FRONT_RIGHT）- A波：A高-B低为正
  void FRONT_RIGHT_BA()
  {
    // 当A跳变为上升沿
    if(digitalRead(FRONT_RIGHT_E2A) == HIGH)
    {
      // B低电压 - 正转
      if (digitalRead(FRONT_RIGHT_E2B) == LOW)
      {
          FRONT_RIGHT_count ++;
      }
      // A高电压 - 反转
      else
      {
        FRONT_RIGHT_count --;
      }
    }
    
    // A跳变到低电平
    else
    {
      // B高电压 - 正转
      if (digitalRead(FRONT_RIGHT_E2B) == HIGH)
      {
        FRONT_RIGHT_count ++;
      }
      // B低电压 - 反转
      else
      {
        FRONT_RIGHT_count --;
      }
    }
  }

  // 3-4.前右（FRONT_RIGHT）- B波：B高-A高为正
  void FRONT_RIGHT_BB()
  {
    // 当B跳转到高电平
    if(digitalRead(FRONT_RIGHT_E2B) == HIGH)
    {
      // A高电压 - 正转
      if (digitalRead(FRONT_RIGHT_E2A) == HIGH)
      {
          FRONT_RIGHT_count ++;
      }
      // A低电压 - 反转
      else
      {
        FRONT_RIGHT_count --;
      }
    }
    
    // B跳变到低电平
    else
    {
      // A低电压 - 正转
      if (digitalRead(FRONT_RIGHT_E2A) == LOW)
      {
        FRONT_RIGHT_count ++;
      }
      // A高电压 - 反转
      else
      {
        FRONT_RIGHT_count --;
      }
    }
  }

  // 3-5.后左（AFTER_LEFT）- A波
  void AFTER_LEFT_DA()
  {
    // 当A跳转到高电平
    if(digitalRead(AFTER_LEFT_E4A) == HIGH)
    {
      // B高电压 - 正转
      if (digitalRead(AFTER_LEFT_E4B) == HIGH)
      {
          AFTER_LEFT_count ++;
      }
      // B低电压 - 反转
      else
      {
        AFTER_LEFT_count --;
      }
    }
    
    // A跳变到低电平
    else
    {
      // B低电压 - 正转
      if (digitalRead(AFTER_LEFT_E4B) == LOW)
      {
        AFTER_LEFT_count ++;
      }
      // B高电压 - 反转
      else
      {
        AFTER_LEFT_count --;
      }
    }
  }

  // 3-6.后左（AFTER_LEFT）- B波
  void AFTER_LEFT_DB()
  {
    // 当B跳变为上升沿
    if(digitalRead(AFTER_LEFT_E4B) == HIGH)
    {
      // A低电压 - 正转
      if (digitalRead(AFTER_LEFT_E4A) == LOW)
      {
          AFTER_LEFT_count ++;
      }
      // A高电压 - 反转
      else
      {
        AFTER_LEFT_count --;
      }
    }
    
    // B跳变到低电平
    else
    {
      // A高电压 - 正转
      if (digitalRead(AFTER_LEFT_E4A) == HIGH)
      {
        AFTER_LEFT_count ++;
      }
      // A低电压 - 反转
      else
      {
        AFTER_LEFT_count --;
      }
    }
  }

    // 3-7.后右（AFTER_RIGHT）- A波
  void AFTER_RIGHT_AA()
  {
        // 当A跳变为上升沿
    if(digitalRead(AFTER_RIGHT_E1A) == HIGH)
    {
      // B低电压 - 正转
      if (digitalRead(AFTER_RIGHT_E1B) == LOW)
      {
          AFTER_RIGHT_count ++;
      }
      // A高电压 - 反转
      else
      {
        AFTER_RIGHT_count --;
      }
    }
    
    // A跳变到低电平
    else
    {
      // B高电压 - 正转
      if (digitalRead(AFTER_RIGHT_E1B) == HIGH)
      {
        AFTER_RIGHT_count ++;
      }
      // B低电压 - 反转
      else
      {
        AFTER_RIGHT_count --;
      }
    }
  }

    // 3-8.后右（AFTER_RIGHT）- B波
  void AFTER_RIGHT_AB()
  {
        // 当B跳转到高电平
    if(digitalRead(AFTER_RIGHT_E1B) == HIGH)
    {
      // A高电压 - 正转
      if (digitalRead(AFTER_RIGHT_E1A) == HIGH)
      {
          AFTER_RIGHT_count ++;
      }
      // A低电压 - 反转
      else
      {
        AFTER_RIGHT_count --;
      }
    }
    
    // B跳变到低电平
    else
    {
      // A低电压 - 正转
      if (digitalRead(AFTER_RIGHT_E1A) == LOW)
      {
        AFTER_RIGHT_count ++;
      }
      // A高电压 - 反转
      else
      {
        AFTER_RIGHT_count --;
      }
    }
  }

  // 4.接收串口命令 ---- 实现编码器数据读、重置函数.i取值是LEFT 或 RIGHT， 是左右轮的标记
  /*
    要分为前左、前右、后左、后右四种情况，包括读取、返回。返回两个就改成返回四个
    FRONT_LEFT、FRONT_RIGHT、AFTER_LEFT、AFTER_RIGHT
  */
  // 4-1.读取一个编码器计数函数
  long readEncoder(int i)
  {
    int pulse = 0;
    if (i == FRONT_LEFT) pulse = FRONT_LEFT_count;
    else if (i == FRONT_RIGHT) pulse = FRONT_RIGHT_count; 
    else if (i == AFTER_LEFT) pulse = AFTER_LEFT_count;
    else if (i == AFTER_RIGHT) pulse = AFTER_RIGHT_count;
    return pulse;
  }
  
  // 4-2.重置一个轮子计数器函数
  void resetEncoder(int i)
  {
    if (i == FRONT_LEFT) FRONT_LEFT_count = 0L;
    else if (i == FRONT_RIGHT) FRONT_RIGHT_count = 0L;
    else if (i == AFTER_LEFT) AFTER_LEFT_count = 0L;
    else if (i == AFTER_RIGHT) AFTER_RIGHT_count = 0L;
    return;
  }
  // 4-3.重置两个轮子函数
  void resetEncoders() 
  {
  resetEncoder(FRONT_LEFT);
  resetEncoder(FRONT_RIGHT);
  resetEncoder(AFTER_LEFT);
  resetEncoder(AFTER_RIGHT);
  }
#else
  #error A encoder driver must be selected!
#endif
#endif

