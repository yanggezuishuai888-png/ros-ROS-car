#include <ros/ros.h>
#include <sensor_msgs/Image.h>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include "net.h"          
#include "yolo11_run/yolo11.h"       
#include <std_msgs/Int32.h>
#include "yolo11_run/humanoid_result.h"

/*
    该文件是通过yolo进行人形检测的。首先订阅image_sub_topic图像数据
    进行yolo识别，通过image_pub_topic发布识别的结果。并将框信息通过
    labels_pub_topic发布出去
*/


class Yolo11Node
{
public:
    Yolo11Node(ros::NodeHandle& nh)
    {
        // ===== 参数 =====
        std::string param_path;
        std::string bin_path;
        std::string image_sub_topic;
        std::string image_pub_topic;
        std::string labels_pub_topic;

        nh.param<std::string>("param_path", param_path, "");                                            // 模型路径
        nh.param<std::string>("bin_path", bin_path, "" ); 
 
        nh.param<std::string>("image_sub_topic", image_sub_topic, "/usb_cam/image_rect_color" );       // 订阅的图像
        nh.param<std::string>("image_pub_topic", image_pub_topic, "/yolo_image_humanoid" );            // 输出图像
        nh.param<std::string>("labels_pub_topic", labels_pub_topic, "/yolo_labels_humanoid" );         // 输出图像
        
        // 不为空
        if (param_path.empty() || bin_path.empty()) 
        {
            ROS_FATAL("Model path is empty! Check launch file.");
            ros::shutdown();
            return;
        }

        // ===== 加载模型 =====
        yolo11.opt.use_vulkan_compute = false;     // 不用GPU
        yolo11.load_param(param_path.c_str());
        yolo11.load_model(bin_path.c_str());

        ROS_INFO("YOLO11 model loaded.");
        ROS_INFO("param: %s", param_path.c_str());
        ROS_INFO("bin:   %s", bin_path.c_str());

        // ===== 订阅 、 发布 =====
        image_sub = nh.subscribe(image_sub_topic, 1, &Yolo11Node::imageCallback, this);    // 订阅图像
        image_pub = nh.advertise<sensor_msgs::Image>(image_pub_topic, 1);                  // 图像结果
        label_pub = nh.advertise<yolo11_run::humanoid_result>(labels_pub_topic, 1);       // 标签
    }

    // 析构函数。类对象周期结束时调用
    ~Yolo11Node()
    {
        cv::destroyAllWindows();
    }

private:
    void imageCallback(const sensor_msgs::ImageConstPtr& image_msg)
    {
        cv_bridge::CvImageConstPtr cv_ptr;
        try
        {
            // ROS Image → cv::Mat (BGR)
            cv_ptr = cv_bridge::toCvShare(image_msg, "bgr8");
        }
        catch (cv_bridge::Exception& e)
        {
            ROS_ERROR("cv_bridge exception: %s", e.what());
            return;
        }

        cv::Mat frame = cv_ptr->image;

        // ===== 推理 =====
        std::vector<Object> objects;
        detect_yolo11(frame, objects, yolo11);

        // ===== 拿标签 =====
        if (!objects.empty())
        {
            Object best;        // 自定义的结构体
            float max_h = 0.0f; // 高度最高 - 距离最近
            bool found = false; // 是否找到变量

            // 遍历所有检测框
            for (auto& obj : objects)
            {
                // 只要 person (COCO label=0)
                if (obj.label == 0)
                {
                    // 选择框高度最大的（最近的人）
                    if (obj.rect.height > max_h)
                    {
                        best = obj;
                        max_h = obj.rect.height;
                        found = true;
                    }
                }
            
            // 如果找到了人
            if (found)
            {
                yolo11_run::humanoid_result msg;

                msg.label  = best.label;
                msg.x      = best.rect.x + best.rect.width * 0.5f;      // 中心坐标
                msg.y      = best.rect.y + best.rect.height * 0.5f;
                msg.width  = best.rect.width;
                msg.height = best.rect.height;

                label_pub.publish(msg);

                ROS_INFO_THROTTLE(1.0,
                    "=======Publish nearest person: h=%.1f , cx=%.1f\n",
                    msg.height, msg.x);
            }
        }
        }
        // ===== 画框 =====
        draw_objects(frame, objects);

        // ===== 发布 ROS Image =====
        cv_bridge::CvImage out_msg;
        out_msg.header = image_msg->header;   // 时间戳 & frame_id
        out_msg.encoding = "bgr8";
        out_msg.image = frame;

        image_pub.publish(out_msg.toImageMsg());

    }

private:
    // 类对象
    ros::Subscriber image_sub;
    ros::Publisher image_pub;
    ros::Publisher label_pub;
    ncnn::Net yolo11;
    
};

int main(int argc, char** argv)
{
    ros::init(argc, argv, "yolo11_node");

    ros::NodeHandle nh;   // 私有命名空间

    Yolo11Node node(nh);

    ros::spin();
    return 0;
}
