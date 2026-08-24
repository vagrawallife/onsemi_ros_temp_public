# syntax=docker/dockerfile:1
# =====================================================================
#  onsemi_ros (robot) Dockerfile  +  DepthVista iToF SDK (runtime)
#  ---------------------------------------------------------------------
#  Based on your onsemi_ros_Dockerfile.txt, with a DepthVista SDK section
#  added so the onsemi_itof ROS node can dlopen libDepthVistaSDK.so.
#
#  WHY: the robot launch (launch_robo.launch.py) runs in THIS image. Your
#  DepthVista .so was baked into the amazing_hand image, which is a DIFFERENT
#  image. So the SDK must be present here too for the iToF node to load it.
#
#  Changes vs your original (all marked with  # >>> ):
#    * Added DepthVista SDK runtime libs (libusb-1.0-0, libudev1, v4l-utils).
#    * COPY DepthVistaViewer -> /opt/depthvista  and set LD_LIBRARY_PATH.
#    * FIX: ENV "KEY = value" (spaces) -> ENV KEY=value  (spaces were baked
#      into the NVIDIA_* values, making them invalid).
#    * FIX: 'pip install -y ...' -> 'pip install ...'  (pip has no -y flag;
#      those lines would fail a fresh build).
#  Everything else is your original, unchanged.
# =====================================================================
FROM arm64v8/ros:jazzy
#FROM osrf/ros:jazzy-desktop-full-noble
USER root
ARG WORKSPACE=dev_ws
ARG ROS_DISTRO=jazzy
WORKDIR /root/$WORKSPACE

# >>> FIX: no spaces around '=' (original baked the spaces into the value)
ENV NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-all}
ENV NVIDIA_DRIVER_CAPABILITIES=${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}graphics
ENV QT_X11_NO_MITSHM=1
ENV EDITOR=nano
ENV XDG_RUNTIME_DIR=/tmp
ENV PIP_BREAK_SYSTEM_PACKAGES=1


RUN apt-get update
RUN apt-get install -y cmake
RUN apt-get install -y curl
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
#RUN apt-get install -y libglu1-mesa-dev
RUN apt-get update
RUN apt-get install -y python3-pydantic
RUN apt-get install -y python3-transforms3d
RUN apt-get update
RUN apt-get install -y libserial-dev
RUN apt-get install -y udev
RUN apt-get install -y usbutils
RUN apt-get clean
RUN apt-get update
RUN apt install -y python3-serial
RUN apt install -y python3-setuptools
RUN apt install -y python3-scipy
RUN apt install -y python3-tk
# cant use numpy 2.0
RUN apt install -y python3-numpy
#RUN pip3 install --force-reinstall numpy==1.22.4
RUN apt-get update
RUN apt-get install -y python3-opencv
# >>> FIX: pip has no -y flag
# RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN pip install --break-system-packages torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu

RUN apt install -y libboost-python-dev
#RUN pip3 install opencv-python
#RUN pip3 uninstall opencv-contrib-python opencv-python
#RUN apt install -y python3-setuptools==58.2.0
#RUN apt install -y  python3-opencv-contrib-python==4.7.0.68
#RUN apt install -y  python3-opencv-python==4.7.0.68
RUN apt update && apt install
RUN apt-get install -y libgstreamer1.0-0
RUN apt-get install -y gstreamer1.0-tools
RUN apt-get install -y gstreamer1.0-plugins-good
RUN apt-get install -y gstreamer1.0-plugins-bad
RUN apt-get install -y gstreamer1.0-plugins-ugly
RUN apt-get install -y gstreamer1.0-libav
#1RUN apt-get install -y libgles2-mesa
RUN apt-get install -y ros-$ROS_DISTRO-joint-state-publisher
RUN apt-get install -y ros-$ROS_DISTRO-robot-localization
#RUN apt-get install -y ros-$ROS_DISTRO-plotjuggler-ros
RUN apt-get install -y ros-$ROS_DISTRO-robot-state-publisher
RUN apt-get install -y ros-$ROS_DISTRO-ros2bag
RUN apt-get install -y ros-$ROS_DISTRO-rosbag2-storage-default-plugins
RUN apt-get install -y ros-$ROS_DISTRO-rqt-tf-tree
RUN apt-get install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp
RUN apt-get install -y ros-$ROS_DISTRO-rmw-cyclonedds-cpp
RUN apt-get install -y ros-$ROS_DISTRO-slam-toolbox
RUN apt-get install -y ros-$ROS_DISTRO-twist-mux
RUN apt-get install -y ros-$ROS_DISTRO-teleop-twist-joy
RUN apt-get install -y ros-$ROS_DISTRO-joy
RUN apt-get install -y ros-$ROS_DISTRO-usb-cam
RUN apt-get install -y ros-$ROS_DISTRO-xacro
RUN apt-get install -y ros-$ROS_DISTRO-controller-manager
RUN apt-get install -y ros-$ROS_DISTRO-tf-transformations
RUN apt-get install -y ros-$ROS_DISTRO-tf2-ros
RUN apt-get install -y ros-$ROS_DISTRO-tf2-tools
RUN apt-get install -y ros-$ROS_DISTRO-ros2-control
RUN apt-get install -y ros-$ROS_DISTRO-ros2-controllers
RUN apt-get install -y ros-$ROS_DISTRO-hardware-interface
RUN apt-get install -y ros-$ROS_DISTRO-joint-state-broadcaster
RUN apt-get install -y ros-$ROS_DISTRO-diff-drive-controller
RUN apt-get install -y ros-$ROS_DISTRO-mecanum-drive-controller
RUN apt-get install -y ros-$ROS_DISTRO-navigation2
RUN apt-get install -y ros-$ROS_DISTRO-nav2-bringup
RUN apt-get install -y ros-$ROS_DISTRO-joint-state-publisher-gui
RUN apt-get install -y ros-$ROS_DISTRO-image-transport-plugins
RUN apt-get install -y ros-$ROS_DISTRO-image-view
RUN apt-get install -y ros-$ROS_DISTRO-rviz2
RUN apt-get install -y ros-$ROS_DISTRO-foxglove-bridge
RUN apt-get install -y ros-$ROS_DISTRO-rtabmap-ros
RUN apt update
RUN apt-get install -y ros-$ROS_DISTRO-vision-opencv
RUN apt-get install -y ros-$ROS_DISTRO-cv-bridge
RUN sudo apt-get update
#RUN sudo apt-get install curl lsb-release gnupg
RUN sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
RUN sudo apt-get update
RUN sudo apt-get install -y gz-harmonic
RUN apt-get update
RUN apt-get install -y ros-$ROS_DISTRO-gz-ros2-control
RUN apt-get install -y libeigen3-dev
RUN apt-get install -y mesa-utils
RUN apt-get install -y dbus-x11

# Install required native system build tools and GUI libraries
RUN apt-get update && apt-get install -y --no-install-recommends 
RUN apt-get install -y build-essential \
    python3-dev \
    libgl1 \
    libglx-mesa0 \
    libxrender1 \
    libxext6 \
    libboost-python-dev libudev-dev \
    libglu1-mesa-dev libxcb-cursor0 mesa-utils dbus-x11 \
    udev usbutils \
    libusb-1.0-0 v4l-utils libgl1 libegl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*


    
# Now run your pip installation
RUN pip install moteus-gui --ignore-installed --break-system-packages

# RUN pip install --upgrade pip && pip install \
#         setuptools \
#         colcon-common-extensions \
#         gradio-imageslider \
#         gradio==4.14.0 \
#         pynput \
#         pyserial \
#         dora-rs-cli \
#         mediapipe==0.10.18 \
#         opencv-python==4.10.0.84 \
#         pyarrow==17.0.0 \
#         scipy==1.14.1 \
#         rustypot \
#         moteus-gui \
#         mujoco \
#         mink \
#         loop-rate-limiters \
#         "qpsolvers[quadprog]"



# # Set environment variables for Intel colcomGPU support
# ENV INTEL_VISIBLE_DEVICES ${INTEL_VISIBLE_DEVICES:-all}
# ENV INTEL_DRIVER_CAPABILITIES ${INTEL_DRIVER_CAPABILITIES:+$INTEL_DRIVER_CAPABILITIES,}graphics
RUN apt-get -y upgrade
RUN echo "source /opt/ros/jazzy/setup.bash" >> /etc/bash.bashrc
#RUN echo "source /home/onsemi/amr_diff/ros2_ws/install/setup.bash" >> /etc/bash.bashrc
#ENTRYPOINT ["/home/onsemi/arm_diff/ros2_ws/src/onsemi_amr/startup.sh"]
#RUN cd /home/onsemi/amr_ros2/dev_ws/src/

# =====================================================================
# >>> DepthVista iToF SDK  (runtime only; used by the onsemi_itof ROS node)
#     The ROS node dlopen()s libDepthVistaSDK.so. This image (not the
#     amazing_hand image) runs the robot launch, so the SDK must live here.
#
#     BUILD CONTEXT REQUIREMENT:
#       Put a  DepthVistaViewer/  folder next to THIS Dockerfile, containing the
#       aarch64  libDepthVistaSDK.so  (+ any dependent .so files) inside it.
#       (Only the .so files are strictly required by the ROS node; copying the
#        whole DepthVistaViewer folder is fine too.)
# =====================================================================
# SDK runtime dependencies (USB + udev + V4L). Your image did not have these.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libusb-1.0-0 libudev1 v4l-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Bring the DepthVista SDK into the image and make it discoverable.
COPY DepthVistaViewer /opt/depthvista/
ENV LD_LIBRARY_PATH="/opt/depthvista:${LD_LIBRARY_PATH}"
# <<< DepthVista iToF SDK
# =====================================================================
# Launcher commands
RUN printf '%s\n' \
    '#!/usr/bin/env bash' 'cd /opt/depthvista' \
    'exec python3 depthvista_camera_live.py "$@"' \
    > /usr/local/bin/depthvista && chmod +x /usr/local/bin/depthvista \
 && printf '%s\n' \
    '#!/usr/bin/env bash' 'cd /opt/depthvista' \
    'exec python3 DepthVistaViewer/depthvista_view_legacy.py "$@"' \
    > /usr/local/bin/depthvista-view && chmod +x /usr/local/bin/depthvista-view

RUN echo "All Done"
