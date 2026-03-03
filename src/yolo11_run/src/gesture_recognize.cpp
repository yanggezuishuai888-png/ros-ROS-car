#include <ros/ros.h>
#include <sensor_msgs/Image.h>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include "net.h"          
#include "yolo11_run/yolo11.h"       
#include <std_msgs/Int32.h>
#include "yolo11_run/detection_result.h"
#include <sensor_msgs/CompressedImage.h>


/*
    该文件是通过yolo进行手势识别的。首先订阅image_sub_topic图像数据
    进行识别，通过image_pub_topic发布识别的结果。并将框信息通过/labels_pub_topic发布出去
*/


std::string image_sub_topic;

class Yolo11Node
{
public:
    Yolo11Node(ros::NodeHandle& nh)
    {
        // ===== 参数 =====
        std::string param_path;
        std::string bin_path;
        // std::string image_sub_topic;
        std::string image_pub_topic;
        std::string labels_pub_topic;

        nh.param<std::string>("param_path", param_path, "");                                        // 模型路径
        nh.param<std::string>("bin_path", bin_path, "" ); 
        nh.param<std::string>("image_sub_topic", image_sub_topic, "/usb_cam/image_rect_color" );    // 订阅的图像
        nh.param<std::string>("image_pub_topic", image_pub_topic, "/yolo_image_gesture" );          // 输出图像
        nh.param<std::string>("labels_pub_topic", labels_pub_topic, "/yolo_labels_gesture" );       // 输出图像
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
        label_pub = nh.advertise<yolo11_run::detection_result>(labels_pub_topic, 1);     // 标签
    }

    // 析构函数。类对象周期结束时调用
    ~Yolo11Node()
    {
        cv::destroyAllWindows();
    }

private:
    void imageCallback(const sensor_msgs::CompressedImageConstPtr& image_msg)
    {
        cv::Mat frame;
        try
        {
            // 解码 compressed image (JPEG)
            frame = cv::imdecode(image_msg->data, cv::IMREAD_COLOR);

            if (frame.empty())
            {
                ROS_WARN("Decoded image is empty!");
                return;
            }
        }
        catch (const std::exception& e)
        {
            ROS_ERROR("Decode exception: %s", e.what());
            return;
        }
        ROS_INFO_THROTTLE(1, "image topic nmae: %s\n\n", image_sub_topic.c_str());

        // ===== 推理 =====
        std::vector<Object> objects;
        detect_yolo11(frame, objects, yolo11);

        // ===== 拿标签 =====
        if (!objects.empty())
        {
            const Object& obj = objects[0];

            yolo11_run::detection_result msg;
            msg.label  = obj.label;
            msg.width  = obj.rect.width;
            msg.height = obj.rect.height;

            label_pub.publish(msg);
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
    ros::init(argc, argv, "gesture_node");

    ros::NodeHandle nh;

    Yolo11Node node(nh);

    ros::spin();
    return 0;
}
