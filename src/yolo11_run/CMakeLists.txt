cmake_minimum_required(VERSION 3.0.2)
project(yolo11_run)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  sensor_msgs
  std_msgs
  cv_bridge
  message_generation
)

find_package(OpenCV REQUIRED)

add_message_files(
  FILES
  detection_result.msg
  humanoid_result.msg
)
generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(CATKIN_DEPENDS roscpp sensor_msgs std_msgs message_runtime)

# 提供头文件路径
set(NCNN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party)

find_package(ncnn REQUIRED
  PATHS ${NCNN_DIR}/lib/cmake/ncnn
)

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${OpenCV_INCLUDE_DIRS}
)

# 将yolo11.cpp编译成静态库给node用
add_library(yolo11_gesture
  src/yolo11_gesture.cpp
)
add_library(yolo11_humanoid
  src/yolo11_humanoid.cpp
)

target_link_libraries(yolo11_gesture
  ncnn
  ${OpenCV_LIBS}
)

target_link_libraries(yolo11_humanoid
  ncnn
  ${OpenCV_LIBS}
)

# ===== ROS node =====
add_executable(gesture_recognize
  src/gesture_recognize.cpp
)
add_executable(humanoid_recognize
  src/humanoid_recognize.cpp
)


target_link_libraries(gesture_recognize
  yolo11_gesture
  ${catkin_LIBRARIES}
)
target_link_libraries(humanoid_recognize
  yolo11_humanoid
  ${catkin_LIBRARIES}
)



