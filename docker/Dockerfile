# syntax=docker/dockerfile:1.7

# =============================================================================
# Stage 1: Build llama-server for Jetson Orin
# =============================================================================
FROM nvcr.io/nvidia/pytorch:23.10-py3 AS llama_builder

ARG LLAMA_CPP_REF=master
ARG CUDA_ARCHITECTURES=87

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone https://github.com/ggml-org/llama.cpp.git

WORKDIR /build/llama.cpp

RUN git checkout "${LLAMA_CPP_REF}"

RUN cmake \
        -S . \
        -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
        -DGGML_CUDA=ON \
        -DGGML_NCCL=OFF \
        -DCMAKE_DISABLE_FIND_PACKAGE_NCCL=ON \
        -DCMAKE_EXE_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -lcuda" \
        -DCMAKE_SHARED_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -lcuda"

RUN cmake \
        --build build \
        --config Release \
        --target llama-server \
        -j"$(nproc)"


# =============================================================================
# Stage 2: Existing onsemi ROS 2 Jazzy robot runtime
# =============================================================================
FROM arm64v8/ros:jazzy

USER root

ARG ROS_DISTRO=jazzy

ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute
ENV QT_X11_NO_MITSHM=1
ENV EDITOR=nano
ENV XDG_RUNTIME_DIR=/tmp
ENV PIP_BREAK_SYSTEM_PACKAGES=1

WORKDIR /root/dev_ws


# =============================================================================
# Base build, Python, USB, serial and GUI dependencies
# =============================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        curl \
        dbus-x11 \
        git \
        gnupg \
        libboost-python-dev \
        libegl1 \
        libgl1 \
        libglx-mesa0 \
        libglu1-mesa-dev \
        libgomp1 \
        libserial-dev \
        libudev-dev \
        libusb-1.0-0 \
        libusb-1.0-0-dev \
        libxcb-cursor0 \
        libxext6 \
        libxrender1 \
        lsb-release \
        mesa-utils \
        python3 \
        python3-dev \
        python3-numpy \
        python3-opencv \
        python3-pip \
        python3-pydantic \
        python3-scipy \
        python3-serial \
        python3-setuptools \
        python3-tk \
        python3-transforms3d \
        sudo \
        udev \
        usbutils \
        v4l-utils && \
    rm -rf /var/lib/apt/lists/*


# =============================================================================
# GStreamer camera/video dependencies
# =============================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gstreamer1.0-libav \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-tools \
        libgstreamer1.0-0 && \
    rm -rf /var/lib/apt/lists/*


# =============================================================================
# Gemma VLA audio runtime dependencies
# =============================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        alsa-utils \
        libasound2-dev \
        psmisc \
        portaudio19-dev \
        pulseaudio-utils && \
    rm -rf /var/lib/apt/lists/*


# =============================================================================
# ROS 2 Jazzy packages already used by the robot
# =============================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-controller-manager \
        ros-${ROS_DISTRO}-cv-bridge \
        ros-${ROS_DISTRO}-diff-drive-controller \
        ros-${ROS_DISTRO}-foxglove-bridge \
        ros-${ROS_DISTRO}-hardware-interface \
        ros-${ROS_DISTRO}-image-transport-plugins \
        ros-${ROS_DISTRO}-image-view \
        ros-${ROS_DISTRO}-joint-state-broadcaster \
        ros-${ROS_DISTRO}-joint-state-publisher \
        ros-${ROS_DISTRO}-joint-state-publisher-gui \
        ros-${ROS_DISTRO}-joy \
        ros-${ROS_DISTRO}-mecanum-drive-controller \
        ros-${ROS_DISTRO}-nav2-bringup \
        ros-${ROS_DISTRO}-navigation2 \
        ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
        ros-${ROS_DISTRO}-rmw-fastrtps-cpp \
        ros-${ROS_DISTRO}-robot-localization \
        ros-${ROS_DISTRO}-robot-state-publisher \
        ros-${ROS_DISTRO}-ros2-control \
        ros-${ROS_DISTRO}-ros2-controllers \
        ros-${ROS_DISTRO}-ros2bag \
        ros-${ROS_DISTRO}-rosbag2-storage-default-plugins \
        ros-${ROS_DISTRO}-rqt-tf-tree \
        ros-${ROS_DISTRO}-rtabmap-ros \
        ros-${ROS_DISTRO}-rviz2 \
        ros-${ROS_DISTRO}-slam-toolbox \
        ros-${ROS_DISTRO}-teleop-twist-joy \
        ros-${ROS_DISTRO}-tf-transformations \
        ros-${ROS_DISTRO}-tf2-ros \
        ros-${ROS_DISTRO}-tf2-tools \
        ros-${ROS_DISTRO}-twist-mux \
        ros-${ROS_DISTRO}-usb-cam \
        ros-${ROS_DISTRO}-vision-opencv \
        ros-${ROS_DISTRO}-xacro && \
    rm -rf /var/lib/apt/lists/*


# =============================================================================
# Gazebo Harmonic and ROS integration
# =============================================================================
RUN curl -fsSL \
        https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release && echo ${UBUNTU_CODENAME}) main" \
        > /etc/apt/sources.list.d/gazebo-stable.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gz-harmonic \
        libeigen3-dev \
        ros-${ROS_DISTRO}-gz-ros2-control && \
    rm -rf /var/lib/apt/lists/*


# =============================================================================
# Existing robot Python dependencies
# =============================================================================
RUN python3 -m pip install \
        --no-cache-dir \
        --break-system-packages \
        torch \
        torchvision \
        torchaudio \
        moteus-gui


# =============================================================================
# Gemma VLA Python dependencies
# =============================================================================
RUN python3 -m pip install \
        --no-cache-dir \
        --break-system-packages \
        attrs \
        certifi \
        espeakng-loader \
        filelock \
        fsspec \
        h5py \
        huggingface_hub \
        numpy==1.26.4 \
        onnx-asr \
        onnxruntime==1.19.2 \
        opencv-python \
        phonemizer-fork \
        pyyaml \
        requests \
        scipy \
        sounddevice \
        soundfile \
        tqdm \
        typing-extensions

RUN python3 -m pip install \
        --no-cache-dir \
        --break-system-packages \
        --no-dependencies \
        kokoro-onnx==0.5.0


# =============================================================================
# Existing DepthVista iToF SDK runtime
# =============================================================================
COPY DepthVistaViewer/ /opt/depthvista/

ENV LD_LIBRARY_PATH=/opt/depthvista:/usr/local/lib:${LD_LIBRARY_PATH}

RUN printf '%s\n' \
        '#!/usr/bin/env bash' \
        'cd /opt/depthvista' \
        'exec python3 depthvista_camera_live.py "$@"' \
        > /usr/local/bin/depthvista && \
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'cd /opt/depthvista' \
        'exec python3 depthvista_view_legacy.py "$@"' \
        > /usr/local/bin/depthvista-view && \
    chmod +x \
        /usr/local/bin/depthvista \
        /usr/local/bin/depthvista-view


# =============================================================================
# Install llama-server built in Stage 1
# =============================================================================
COPY --from=llama_builder \
    /build/llama.cpp/build/bin/llama-server \
    /usr/local/bin/llama-server

COPY --from=llama_builder \
    /build/llama.cpp/build/bin/*.so* \
    /usr/local/lib/

RUN ldconfig


# =============================================================================
# Gemma VLA convenience command
#
# Gemma4_vla.py is supplied by the bind-mounted ROS workspace at runtime:
#   ros2_ws/src/onsemi_gemma_vla/Gemma4_vla.py
# =============================================================================
RUN printf '%s\n' \
        '#!/usr/bin/env bash' \
        'set -e' \
        'VLA_SCRIPT=/home/onsemi/onsemi_ros/ros2_ws/src/onsemi_gemma_vla/Gemma4_vla.py' \
        'if [ ! -f "${VLA_SCRIPT}" ]; then' \
        '  echo "Gemma VLA script not found: ${VLA_SCRIPT}" >&2' \
        '  exit 1' \
        'fi' \
        'exec python3 "${VLA_SCRIPT}" "$@"' \
        > /usr/local/bin/gemma-vla-client && \
    chmod +x /usr/local/bin/gemma-vla-client


# =============================================================================
# Shell initialization and default working directory
# =============================================================================
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /etc/bash.bashrc

WORKDIR /home/onsemi/onsemi_ros/ros2_ws

CMD ["bash"]
