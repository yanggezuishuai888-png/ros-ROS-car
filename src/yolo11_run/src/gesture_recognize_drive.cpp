#include <ros/ros.h>
#include <geometry_msgs/Twist.h>
#include "yolo11_run/detection_result.h"
#include <cmath>
#include <algorithm>


// =================== 距离控制参数 ===================
constexpr float REAL_HAND_HEIGHT = 0.15f;
constexpr float FOCAL_LENGTH     = 461.8f;
constexpr float TARGET_DIST      = 2.0f;

// =================== 当前状态 ===================
int   current_label    = 2;
float current_distance = 10.0f;

// =================== 动作锁 ===================
bool action_running = false;
ros::Time action_end_time;

// 发布器
ros::Publisher cmd_pub;

// =================== 速度计算 ===================
float computeLinearSpeed(float distance)
{
    float error = distance - TARGET_DIST;

    if (fabs(error) < 0.15f)
        return 0.0f;

    float Kp = 0.6f;
    float v = Kp * error;

    v = std::max(std::min(v, 0.4f), -0.4f);
    return v;
}

// =================== 保留你原本的动作生成 ===================
geometry_msgs::Twist generateCmd(int label, float distance, float turn_v)
{
    geometry_msgs::Twist cmd;
    // float v = computeLinearSpeed(distance);
    float v = distance;

    switch (label)
    {
    case 0: // 后退
        cmd.linear.x = -fabs(v);
        break;

    case 1: // 前进
        cmd.linear.x = fabs(v);
        break;

    case 2: // 停止
        cmd.linear.x = 0;
        cmd.angular.z = 0;
        break;

    case 3: // 原地转圈
        cmd.angular.z = 0.8;
        break;

    case 4: // 左前
        cmd.linear.x = fabs(v);
        cmd.angular.z = turn_v;
        break;

    case 5: // 右前
        cmd.linear.x = fabs(v);
        cmd.angular.z = -turn_v;
        break;

    case 6: // 左后
        cmd.linear.x = -fabs(v);
        cmd.angular.z = turn_v;
        break;

    case 7: // 右后
        cmd.linear.x = -fabs(v);
        cmd.angular.z = -turn_v;
        break;

    default:
        break;
    }

    return cmd;
}

// =================== 每个动作持续时间 ===================
float getActionDuration(int label)
{
    switch (label)
    {
    case 0: return 3.0; // 后退 1s
    case 1: return 3.0; // 前进 1s
    case 2: return 0.0; // 停止
    case 3: return 7.0; // 原地转圈 5s
    case 4: return 5.0; // 左前 2s
    case 5: return 5.0; // 右前 2s
    case 6: return 5.0; // 左后 2s
    case 7: return 5.0; // 右后 2s
    default: return 0.0;
    }
}

// =================== 手势回调（触发动作） ===================
void detectionCallback(const yolo11_run::detection_result::ConstPtr& msg)
{
    // 动作执行期间，忽略新手势
    if (action_running)
        return;

    current_label = msg->label;

    // 距离更新
    // float pixel_height = msg->height;
    // if (pixel_height > 1.0f)
    // {
    //     current_distance =
    //         (REAL_HAND_HEIGHT * FOCAL_LENGTH) / pixel_height;
    // }

    // 设置动作时间
    float duration = getActionDuration(current_label);

    if (duration > 0.0)
    {
        action_running = true;                                          
        action_end_time = ros::Time::now() + ros::Duration(duration);   // 执行的时间

        ROS_INFO("Gesture %d triggered action for %.1f seconds",
                 current_label, duration);
    }
}

// =================== 主函数 ===================
int main(int argc, char** argv)
{
    ros::init(argc, argv, "gesture_action_node");
    ros::NodeHandle nh;

    ros::Subscriber sub =
        nh.subscribe("/yolo_labels_gesture", 1, detectionCallback);

    cmd_pub =
        nh.advertise<geometry_msgs::Twist>("/cmd_vel", 1);

    ros::Rate loop(30);

    while (ros::ok())
    {
        geometry_msgs::Twist cmd;

        if (action_running)
        {
            // 动作时间到 → 停止并解锁
            if (ros::Time::now() > action_end_time)
            {
                action_running = false;
                current_label = 2;

                ROS_INFO("Action finished. Waiting next gesture.");
            }
            else
            {
                // 动作期间持续发布速度
                cmd = generateCmd(current_label, 1, 0.8);
                // cmd = generateCmd(current_label, current_distance, 0.3);
            }
        }
        else
        {
            // 没动作 → 停车
            cmd.linear.x = 0;
            cmd.angular.z = 0;
        }

        cmd_pub.publish(cmd);

        ros::spinOnce();
        loop.sleep();
    }

    return 0;
}
