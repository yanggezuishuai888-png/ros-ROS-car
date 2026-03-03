#!/bin/sh

if [ -n "$DESTDIR" ] ; then
    case $DESTDIR in
        /*) # ok
            ;;
        *)
            /bin/echo "DESTDIR argument must be absolute... "
            /bin/echo "otherwise python's distutils will bork things."
            exit 1
    esac
fi

echo_and_run() { echo "+ $@" ; "$@" ; }

echo_and_run cd "/home/rm/workspace/four_wheel_differential_cal/src/ros_arduino_bridge-indigo-devel/ros_arduino_python"

# ensure that Python install destination exists
echo_and_run mkdir -p "$DESTDIR/home/rm/workspace/four_wheel_differential_cal/install/lib/python3/dist-packages"

# Note that PYTHONPATH is pulled from the environment to support installing
# into one location when some dependencies were installed in another
# location, #123.
echo_and_run /usr/bin/env \
    PYTHONPATH="/home/rm/workspace/four_wheel_differential_cal/install/lib/python3/dist-packages:/home/rm/workspace/four_wheel_differential_cal/build/lib/python3/dist-packages:$PYTHONPATH" \
    CATKIN_BINARY_DIR="/home/rm/workspace/four_wheel_differential_cal/build" \
    "/usr/bin/python3" \
    "/home/rm/workspace/four_wheel_differential_cal/src/ros_arduino_bridge-indigo-devel/ros_arduino_python/setup.py" \
     \
    build --build-base "/home/rm/workspace/four_wheel_differential_cal/build/ros_arduino_bridge-indigo-devel/ros_arduino_python" \
    install \
    --root="${DESTDIR-/}" \
    --install-layout=deb --prefix="/home/rm/workspace/four_wheel_differential_cal/install" --install-scripts="/home/rm/workspace/four_wheel_differential_cal/install/bin"
