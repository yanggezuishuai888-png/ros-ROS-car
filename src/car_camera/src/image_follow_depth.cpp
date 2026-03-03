#include <ros/ros.h>
#include <cv_bridge/cv_bridge.h>
#include <sensor_msgs/image_encodings.h>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>  // 显示图像
#include <geometry_msgs/Twist.h>


using namespace cv;  // 所有没指明命名空间的优先调用cv这个命名空间下的同名函数，cv是opencv的命名空间。省去cv前缀
using namespace std;


// hsv滑杆变量
static int iLowH = 0;
static int iHighH = 10;

static int iLowS = 100;
static int iHighS = 255;

static int iLowV = 100;
static int iHighV = 255;

// 消息发布相关
geometry_msgs::Twist vel_cmd;
ros::Publisher vel_pub;


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
    // 拿到cv图像
    Mat imgOriginal = cv_ptr->image;
    
    // 将RGB转HSV
    Mat imgHSV;
    cvtColor(imgOriginal, imgHSV, COLOR_BGR2HSV);

    // 在HSV空间做直方图均衡化（对V）
    vector<Mat> hsvSplit;                   // 定义Mat数组，0-H，1-S，2-V
    split(imgHSV, hsvSplit);                // 把三个单通道Mat分别放到数组里
    equalizeHist(hsvSplit[2], hsvSplit[2]); // 对V做直方图均衡化（让暗处更亮，亮出层次分明）
    merge(hsvSplit,imgHSV);                 // 将三通道重新合起来

    // 按照HSV值对图像进行二值化。即对每个像素点HSV做判断，小于HSV最低值为黑，大于为白
    Mat imgThresholded;
    inRange(imgHSV, Scalar(iLowH, iLowS, iLowV), Scalar(iHighH, iHighS, iHighV), imgThresholded); 

    // 开操作(去噪点)
    Mat element = getStructuringElement(MORPH_RECT, Size(5, 5));        // 创建扫描矩阵。MORPH_RECT-表示形状为矩形
    morphologyEx(imgThresholded, imgThresholded, MORPH_OPEN, element);  // 开操作。输入图像变量，输出图像变量，操作类型（开），扫描矩阵

    // 闭操作(连接连通域)
    morphologyEx(imgThresholded, imgThresholded, MORPH_CLOSE, element); // 闭操作。输入图像变量，输出图像变量，操作类型（闭），扫描矩阵
    
    // 遍历二值化后的图像数据
    int nTargetX = 0;                               // 目标像素点图像X坐标像素值之和
    int nTargetY = 0;                               // 目标像素点图像Y坐标像素值之和
    int nPixCount = 0;                              // 目标像素点数
    int nImgWidth = imgThresholded.cols;            // 获取图像宽
    int nImgHeight = imgThresholded.rows;           // 获取图像高
    int nImgChannels = imgThresholded.channels();   // 获取图像通道数
    int minY = nImgHeight;                          // 最小y值
    int maxY = 0;                                   // 最大y值
    // ===== 单目测距参数 =====
    static float fy = 461.8f;          // 相机内参 fy（像素）
    static float real_person_h = 0.02; // 人真实高度（米）
    static float target_dist = 0.5;    // 跟随目标距离（米）
    
    for (int y = 0; y < nImgHeight; y++)
    {
        for (int x = 0; x < nImgWidth; x++)
        {   // 检查像素是否为255.因为data中的像素不是二维矩阵，
            // 而是一维列表（将二维拆成了一维），所以需要将一维中
            // 找到像素位置。其中y*nImageWidth表示y行前右多少个像素，再加上这一行的x个像素，就为像素位置
            if (imgThresholded.data[y*nImgWidth + x] == 255)  
            {
                nTargetX += x;
                nTargetY += y;
                nPixCount ++;
                // 获取最小、最大的y像素值
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
    }
    // 存在白点
    if (nPixCount > 0)
    {   // 将目标所有像素值X Y位置 / 总点数。得到他的质心X Y值
        nTargetX /= nPixCount;
        nTargetY /= nPixCount;
        // printf("颜色质心坐标（%d, %d) 点数 = %d\n", nTargetX, nTargetY, nPixCount);
        // 画坐标
        int thickness = 3;          // 线宽
        int lineTyepe = LINE_8;     // 线型
            // 横线
        Point line_begin = Point(nTargetX-10, nTargetY);
        Point line_end = Point(nTargetX+10, nTargetY);
            // 图像，起始位置，终点位置，颜色，线宽，线型
        line(imgOriginal, line_begin, line_end, Scalar(0, 255, 0), thickness, lineTyepe);
            // 竖线
        line_begin.x = nTargetX;
        line_begin.y = nTargetY - 10;
        line_end.x = nTargetX;
        line_end.y = nTargetY + 10;
        line(imgOriginal, line_begin, line_end, Scalar(0, 255, 0), thickness, lineTyepe);

        // 单目测距（米）
        int goal_h = maxY - minY;                           // 物体高
        float dist = (real_person_h * fy) / goal_h;
        // 速度信息 
        float err_dist = dist - target_dist;                // 计算需要保持的距离
        float fvelfoward = err_dist * 0.6;                  // 前进速度
        float fvelturn = (nImgWidth/2 - nTargetX) * 0.003;  // 转弯速度
        // 最大速度限制
        if (fvelfoward > 0.3) fvelfoward = 0.3;
        if (fvelturn > 0.3) fvelturn = 0.3;
        vel_cmd.linear.x = fvelfoward;
        vel_cmd.linear.y = 0;
        vel_cmd.linear.z = 0;
        vel_cmd.angular.x = 0;
        vel_cmd.angular.y = 0;
        vel_cmd.angular.z = fvelturn;

        printf("距离值：%.2f, 物体像素高：%d\n", dist, goal_h);
    }   
    else
    {
        // printf("目标颜色消失... 尝试寻找目标\n");
        vel_cmd.linear.x = 0;
        vel_cmd.linear.y = 0;
        vel_cmd.linear.z = 0;
        vel_cmd.angular.x = 0;
        vel_cmd.angular.y = 0;
        vel_cmd.angular.z = 0.02;
    }
    vel_pub.publish(vel_cmd);
    // printf("机器人运动速度(linear.x= %.2f, angular.z= %.2f)\n", vel_cmd.linear.x, vel_cmd.angular.z);
    // 显示处理结果
    imshow("RGB", imgOriginal); 
    imshow("HSV", imgHSV); 
    imshow("Result", imgThresholded); 
    waitKey(5);  // 给当前线程等待的时间（opencv函数）
}


int main(int argc, char **argv)
{
    ros::init(argc, argv, "image_follow");
    
    // 对象
    ros::NodeHandle nh("~");

    // 订阅。1时缓冲队列
    ros::Subscriber rgb_sub = nh.subscribe("/usb_cam/image_rect_color", 1, Cam_RGB_Callback);
    // 发布者。话题名称，消息队列
    vel_pub = nh.advertise<geometry_msgs::Twist>("/cmd_vel", 30);

    // hsv调节窗口。窗口名称，
    namedWindow("Threshold", WINDOW_AUTOSIZE);
    
    // 创建滑杆。滑杆名称，所属窗口名称，滑杆变量 
    createTrackbar("LowH", "Threshold", &iLowH, 179);
    createTrackbar("HighH", "Threshold", &iHighH, 179);

    createTrackbar("LowS", "Threshold", &iLowS, 255);
    createTrackbar("HighS", "Threshold", &iHighS, 255);

    createTrackbar("LowV", "Threshold", &iLowV, 255);
    createTrackbar("HighV", "Threshold", &iHighV, 255);

    // 图像显示窗口
    namedWindow("RGB");
    namedWindow("HSV");
    namedWindow("Result");

    ros::spin();
}