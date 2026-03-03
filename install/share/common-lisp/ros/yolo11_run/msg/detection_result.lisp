; Auto-generated. Do not edit!


(cl:in-package yolo11_run-msg)


;//! \htmlinclude detection_result.msg.html

(cl:defclass <detection_result> (roslisp-msg-protocol:ros-message)
  ((label
    :reader label
    :initarg :label
    :type cl:integer
    :initform 0)
   (width
    :reader width
    :initarg :width
    :type cl:float
    :initform 0.0)
   (height
    :reader height
    :initarg :height
    :type cl:float
    :initform 0.0))
)

(cl:defclass detection_result (<detection_result>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <detection_result>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'detection_result)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name yolo11_run-msg:<detection_result> is deprecated: use yolo11_run-msg:detection_result instead.")))

(cl:ensure-generic-function 'label-val :lambda-list '(m))
(cl:defmethod label-val ((m <detection_result>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader yolo11_run-msg:label-val is deprecated.  Use yolo11_run-msg:label instead.")
  (label m))

(cl:ensure-generic-function 'width-val :lambda-list '(m))
(cl:defmethod width-val ((m <detection_result>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader yolo11_run-msg:width-val is deprecated.  Use yolo11_run-msg:width instead.")
  (width m))

(cl:ensure-generic-function 'height-val :lambda-list '(m))
(cl:defmethod height-val ((m <detection_result>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader yolo11_run-msg:height-val is deprecated.  Use yolo11_run-msg:height instead.")
  (height m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <detection_result>) ostream)
  "Serializes a message object of type '<detection_result>"
  (cl:let* ((signed (cl:slot-value msg 'label)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:let ((bits (roslisp-utils:encode-single-float-bits (cl:slot-value msg 'width))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-single-float-bits (cl:slot-value msg 'height))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <detection_result>) istream)
  "Deserializes a message object of type '<detection_result>"
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'label) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'width) (roslisp-utils:decode-single-float-bits bits)))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'height) (roslisp-utils:decode-single-float-bits bits)))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<detection_result>)))
  "Returns string type for a message object of type '<detection_result>"
  "yolo11_run/detection_result")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'detection_result)))
  "Returns string type for a message object of type 'detection_result"
  "yolo11_run/detection_result")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<detection_result>)))
  "Returns md5sum for a message object of type '<detection_result>"
  "102e07918dfac06e9f14dad29fca803a")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'detection_result)))
  "Returns md5sum for a message object of type 'detection_result"
  "102e07918dfac06e9f14dad29fca803a")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<detection_result>)))
  "Returns full string definition for message of type '<detection_result>"
  (cl:format cl:nil "int32 label~%float32 width~%float32 height~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'detection_result)))
  "Returns full string definition for message of type 'detection_result"
  (cl:format cl:nil "int32 label~%float32 width~%float32 height~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <detection_result>))
  (cl:+ 0
     4
     4
     4
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <detection_result>))
  "Converts a ROS message object to a list"
  (cl:list 'detection_result
    (cl:cons ':label (label msg))
    (cl:cons ':width (width msg))
    (cl:cons ':height (height msg))
))
