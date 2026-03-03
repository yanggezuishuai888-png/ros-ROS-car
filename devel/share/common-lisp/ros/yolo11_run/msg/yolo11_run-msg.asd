
(cl:in-package :asdf)

(defsystem "yolo11_run-msg"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "detection_result" :depends-on ("_package_detection_result"))
    (:file "_package_detection_result" :depends-on ("_package"))
    (:file "humanoid_result" :depends-on ("_package_humanoid_result"))
    (:file "_package_humanoid_result" :depends-on ("_package"))
  ))