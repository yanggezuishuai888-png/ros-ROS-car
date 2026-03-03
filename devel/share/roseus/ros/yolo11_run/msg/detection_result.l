;; Auto-generated. Do not edit!


(when (boundp 'yolo11_run::detection_result)
  (if (not (find-package "YOLO11_RUN"))
    (make-package "YOLO11_RUN"))
  (shadow 'detection_result (find-package "YOLO11_RUN")))
(unless (find-package "YOLO11_RUN::DETECTION_RESULT")
  (make-package "YOLO11_RUN::DETECTION_RESULT"))

(in-package "ROS")
;;//! \htmlinclude detection_result.msg.html


(defclass yolo11_run::detection_result
  :super ros::object
  :slots (_label _width _height ))

(defmethod yolo11_run::detection_result
  (:init
   (&key
    ((:label __label) 0)
    ((:width __width) 0.0)
    ((:height __height) 0.0)
    )
   (send-super :init)
   (setq _label (round __label))
   (setq _width (float __width))
   (setq _height (float __height))
   self)
  (:label
   (&optional __label)
   (if __label (setq _label __label)) _label)
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
   ;; float32 _width
     (setq _width (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _height
     (setq _height (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;;
   self)
  )

(setf (get yolo11_run::detection_result :md5sum-) "102e07918dfac06e9f14dad29fca803a")
(setf (get yolo11_run::detection_result :datatype-) "yolo11_run/detection_result")
(setf (get yolo11_run::detection_result :definition-)
      "int32 label
float32 width
float32 height

")



(provide :yolo11_run/detection_result "102e07918dfac06e9f14dad29fca803a")


