#pragma once
#include <opencv2/opencv.hpp>
#include <vector>
#include "net.h"

struct Object
{
    cv::Rect_<float> rect;
    int label;
    float prob;
};

void detect_yolo11(const cv::Mat& bgr,
                   std::vector<Object>& objects,
                   ncnn::Net& yolo11);

void draw_objects(const cv::Mat& bgr,
                  const std::vector<Object>& objects);
