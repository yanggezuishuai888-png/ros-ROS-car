cmake_minimum_required(VERSION 3.0.2)
project(car_camera)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  cv_bridge
)
find_package(OpenCV REQUIRED)

# 向外提供依赖
catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES car_camera
#  CATKIN_DEPENDS roscpp rospy std_msgs
#  DEPENDS system_lib
)

# 给cpp添加头文件路径
include_directories(
  ${catkin_INCLUDE_DIRS}
  # cv头文件
  ${OpenCV_INCLUDE_DIRS}
)

# 指定编译文件
add_executable(image_sub src/image_sub.cpp)
add_executable(image_recognize_hsv src/image_recognize_hsv.cpp)
add_executable(image_follow_center src/image_follow.cpp)
add_executable(image_follow_depth src/image_follow_depth.cpp)

# 指定编译顺序
add_dependencies(image_sub ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
add_dependencies(image_recognize_hsv ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
add_dependencies(image_follow_depth ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
add_dependencies(image_follow_center ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# 指定链接对象
target_link_libraries(image_sub
  ${catkin_LIBRARIES}
  ${OpenCV_LIBS}
)
target_link_libraries(image_recognize_hsv
  ${catkin_LIBRARIES}
  ${OpenCV_LIBS}
)
target_link_libraries(image_follow_depth
  ${catkin_LIBRARIES}
  ${OpenCV_LIBS}
)

target_link_libraries(image_follow_center
  ${catkin_LIBRARIES}
  ${OpenCV_LIBS}
)

