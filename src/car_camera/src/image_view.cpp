#include <iostream>
#include <opencv2/opencv.hpp>

int main() {
    // 0 表示第一个摄像头，如果你有多个，可以试试 1、2 ...
    cv::VideoCapture cap(0);

    if (!cap.isOpened()) {
        std::cerr << "无法打开摄像头！请检查 /dev/video* 或 VMware USB 连接。\n";
        return -1;
    }

    // 可选：设置分辨率
    cap.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, 480);

    cv::Mat frame;

    while (true) {
        cap >> frame;              // 读取一帧
        if (frame.empty()) {
            std::cerr << "读取到空帧，退出。\n";
            break;
        }

        cv::imshow("USB Camera", frame);  // 显示画面

        // waitKey(1)：等待按键 1ms
        // 如果按下 q 或 ESC 就退出
        char key = (char)cv::waitKey(1);
        if (key == 27 || key == 'q') {   // 27 = ESC
            break;
        }
    }

    cap.release();
    cv::destroyAllWindows();
    return 0;
}
