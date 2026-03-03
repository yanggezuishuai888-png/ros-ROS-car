#include <ros/ros.h>
#include <cv_bridge/cv_bridge.h>
#include <sensor_msgs/image_encodings.h>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>  // 显示图像

using namespace cv;  // 所有没指明命名空间的优先调用cv这个命名空间下的同名函数，cv是opencv的命名空间。省去cv前缀

void Cam_RGB_Callback(const sensor_msgs::ImageConstPtr& msg)
{
    // 定义opencv类对象（和指针性质相同）
    cv_bridge::CvImagePtr cv_ptr;
    try
    {
        // ros转cv。cv_ptr中包括image消息、编码信息、cv图像
        cv_ptr = cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::BGR8);
    }

    catch (cv_bridge::Exception& e)
    {
        ROS_ERROR("cv_bridge exception: %s", e.what());
        return;
    }
    
    Mat imgOriginal = cv_ptr->image;
    imshow("RGB", imgOriginal);
    waitKey(1);
}

int main(int argc, char **argv)
{
    ros::init(argc, argv, "image_sub");
    
    // 对象
    ros::NodeHandle nh("~");

    // 订阅。1时缓冲队列
    ros::Subscriber rgb_sub = nh.subscribe("/usb_cam/image_rect_color", 1, Cam_RGB_Callback);

    // 创建RGB窗口
    namedWindow("RGB");
    ros::spin();
}