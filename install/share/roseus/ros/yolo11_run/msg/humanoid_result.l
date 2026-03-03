;; Auto-generated. Do not edit!


(when (boundp 'yolo11_run::humanoid_result)
  (if (not (find-package "YOLO11_RUN"))
    (make-package "YOLO11_RUN"))
  (shadow 'humanoid_result (find-package "YOLO11_RUN")))
(unless (find-package "YOLO11_RUN::HUMANOID_RESULT")
  (make-package "YOLO11_RUN::HUMANOID_RESULT"))

(in-package "ROS")
;;//! \htmlinclude humanoid_result.msg.html


(defclass yolo11_run::humanoid_result
  :super ros::object
  :slots (_label _x _y _width _height ))

(defmethod yolo11_run::humanoid_result
  (:init
   (&key
    ((:label __label) 0)
    ((:x __x) 0.0)
    ((:y __y) 0.0)
    ((:width __width) 0.0)
    ((:height __height) 0.0)
    )
   (send-super :init)
   (setq _label (round __label))
   (setq _x (float __x))
   (setq _y (float __y))
   (setq _width (float __width))
   (setq _height (float __height))
   self)
  (:label
   (&optional __label)
   (if __label (setq _label __label)) _label)
  (:x
   (&optional __x)
   (if __x (setq _x __x)) _x)
  (:y
   (&optional __y)
   (if __y (setq _y __y)) _y)
  (:width
   (&optional __width)
   (if __width (setq _width __width)) _width)
  (:height
   (&optional __height)
   (if __height (setq _height __height)) _height)
  (:serialization-length
   ()
   (+
    ;; int32 _label
    4
    ;; float32 _x
    4
    ;; float32 _y
    4
    ;; float32 _width
    4
    ;; float32 _height
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _label
       (write-long _label s)
     ;; float32 _x
       (sys::poke _x (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _y
       (sys::poke _y (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _width
       (sys::poke _width (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _height
       (sys::poke _height (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _label
     (setq _label (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; float32 _x
     (setq _x (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _y
     (setq _y (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _width
     (setq _width (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _height
     (setq _height (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;;
   self)
  )

(setf (get yolo11_run::humanoid_result :md5sum-) "acafaa5e6ebdce3b37c19fdc2b2d3b69")
(setf (get yolo11_run::humanoid_result :datatype-) "yolo11_run/humanoid_result")
(setf (get yolo11_run::humanoid_result :definition-)
      "int32 label        # 类别ID，例如0=person

float32 x          # bbox中心x (像素)
float32 y          # bbox中心y (像素)

float32 width      # bbox宽度 (像素)
float32 height     # bbox高度 (像素)
")



(provide :yolo11_run/humanoid_result "acafaa5e6ebdce3b37c19fdc2b2d3b69")


