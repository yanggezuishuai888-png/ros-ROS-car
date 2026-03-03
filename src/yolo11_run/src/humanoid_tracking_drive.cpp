#include <ros/ros.h>
#include <geometry_msgs/Twist.h>
#include "yolo11_run/humanoid_result.h"

/*
    该文件是拿到yolo识别结果（label、框高、中心点）后，基于该信息控制小车跟随人（主要的控制参数都在这里了）
*/


// =================== 识别参数 ===================
constexpr float REAL_PERSON_HEIGHT = 1.6f;  // 目标真实高度
constexpr float FOCAL_LENGTH = 461.8f;      // 内参
constexpr float TARGET_DIST = 2.0f;         // 保持的距离
bool person_detected = false;               // 是否收到人框信息
float current_distance = 10.0f;             // 真实距离  
float current_cx = 0.0f;                    // 中心坐标
float current_h = 0.0f;                     //
int image_width = 640;                      // 图像宽度

// =================== 控制参数 ===================
constexpr float KP_DIST = 0.5f;             // 线速度比例 
constexpr float KP_TURN = 0.003f;           // 角速度比例
constexpr float MAX_V = 0.3f;               // 最大速度限制
constexpr float MAX_W = 0.2f;   


// =================== 线速度控制 ===================
float computeLinearSpeed(float dist)
{   
    // 需要走的距离
    float error = dist - TARGET_DIST;

    if (fabs(error) < 0.2f)
        return 0.0f;

    float v = KP_DIST * error;

    v = std::max(std::min(v, MAX_V), -MAX_V);
    return v;
}

// =================== 角速度控制（居中） ===================
float computeAngularSpeed(float cx)
{
    float center_x = image_width / 2.0f;
    float error_x = center_x - cx;

    float w = KP_TURN * error_x;

    // 最大转弯速度限制 0.4
    w = std::max(std::min(w, MAX_W), -MAX_W);

    return w;
}

// =================== 发布速度命令 ===================
geometry_msgs::Twist generateFollowCmd()
{
    geometry_msgs::Twist cmd;

    // 没有检测到人
    if (!person_detected)
    {
        cmd.linear.x = 0;
        cmd.angular.z = 0;
        return cmd;
    }
    // 线速度角速度居中
    cmd.linear.x = computeLinearSpeed(current_distance);
    cmd.angular.z = computeAngularSpeed(current_cx);

    return cmd;
}

// =================== YOLO检测回调 ===================
void detectionCallback(const yolo11_run::humanoid_result::ConstPtr& msg)
{
    // 只处理人（0）
    if (msg->label == 0)
    {
        // 识别到人变量
        person_detected = true;

        current_cx = msg->x;
        current_h  = msg->height;

        // 单目测距（height越大越近）
        if (current_h > 5.0f)
        {
            // 真实距离
            current_distance = (REAL_PERSON_HEIGHT * FOCAL_LENGTH) / current_h;

            ROS_INFO_THROTTLE(1.0, "Nearest person: dist=%.2f m, h=%.1f px, cx=%.1f",
                              current_distance, current_h, current_cx);
        }
    }
    else
    {
        person_detected = false;
    }
}

// =================== 主函数 ===================
int main(int argc, char** argv)
{
    ros::init(argc, argv, "humanoid_follow_node");
    ros::NodeHandle nh;

    // 从launch读取图像宽度
    nh.param("image_width", image_width, 640);

    ros::Subscriber sub = nh.subscribe("/yolo_labels_humanoid", 1, detectionCallback);

    ros::Publisher cmd_pub = nh.advertise<geometry_msgs::Twist>("/cmd_vel", 1);

    ros::Rate loop(1);

    while (ros::ok())
    {   
        // 计算速度
        geometry_msgs::Twist cmd = generateFollowCmd();
        cmd_pub.publish(cmd);
        
        ros::spinOnce();
        loop.sleep();
    }

    return 0;
}
