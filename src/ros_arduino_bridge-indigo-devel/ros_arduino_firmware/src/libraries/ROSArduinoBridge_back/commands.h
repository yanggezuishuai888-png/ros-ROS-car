/* Define single-letter commands that will be sent by the PC over the
   serial link.
*/

#ifndef COMMANDS_H
#define COMMANDS_H

#define ANALOG_READ    'a'  // 读第一个参数的模拟口值并打印
#define GET_BAUDRATE   'b'  // 打印波特率
#define PIN_MODE       'c'  // 设置管脚模式。0为输入、1为输出
#define DIGITAL_READ   'd'  // 读第一个参数的数字引脚值并打印
#define READ_ENCODERS  'e'  // 读取两个轮子的编码器计数数据
#define MOTOR_SPEEDS   'm'  // 电机转速。示例：m 100 100
#define PING           'p'  // 超声波等传感器函数调用
#define RESET_ENCODERS 'r'  // 重置两个轮子的编码器计数的数值 
#define SERVO_WRITE    's'  // 伺服电机相关
#define SERVO_READ     't'  // 伺服电机相关
#define UPDATE_PID     'u'  // 设置PID增益
#define DIGITAL_WRITE  'w'  // 设置高低电平。0为低，1为高
#define ANALOG_WRITE   'x'  // 设置模拟值。示例：x 3 255
// 编码器中电机位置标识符（用字符串比较麻烦，要调用函数）
#define FRONT_LEFT            0   
#define FRONT_RIGHT           1
#define AFTER_LEFT            2   
#define AFTER_RIGHT           3

#define LEFT                  0   
#define RIGHT                 1



#endif
