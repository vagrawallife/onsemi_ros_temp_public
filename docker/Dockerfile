# syntax=docker/dockerfile:1.7
FROM nvcr.io/nvidia/pytorch:23.10-py3 AS llama_builder
ARG CUDA_ARCHITECTURES=87
ARG LLAMA_CPP_REF=master
RUN apt-get update && apt-get install -y git cmake build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone https://github.com/ggml-org/llama.cpp.git && cd llama.cpp && git checkout "${LLAMA_CPP_REF}" && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" -DGGML_CUDA=ON -DGGML_NCCL=OFF -DCMAKE_DISABLE_FIND_PACKAGE_NCCL=ON -DCMAKE_EXE_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -lcuda" -DCMAKE_SHARED_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -lcuda" && cmake --build build --target llama-server -j"$(nproc)"

FROM arm64v8/ros:jazzy
USER root
ARG ROS_DISTRO=jazzy
ARG VLA_REF=82c6ce7fd06eca3b8f28e32c6d5c615ceb973484
ENV DEBIAN_FRONTEND=noninteractive NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute QT_X11_NO_MITSHM=1 EDITOR=nano XDG_RUNTIME_DIR=/tmp PIP_BREAK_SYSTEM_PACKAGES=1 PYTHONPATH=/opt/gemma_vla
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake curl git gnupg lsb-release sudo python3 python3-dev python3-pip python3-pydantic python3-transforms3d python3-serial python3-setuptools python3-scipy python3-tk python3-numpy python3-opencv libserial-dev libboost-python-dev libudev-dev libusb-1.0-0 libusb-1.0-0-dev udev usbutils v4l-utils libgl1 libegl1 libgomp1 libglx-mesa0 libglu1-mesa-dev mesa-utils libxrender1 libxext6 libxcb-cursor0 dbus-x11 libgstreamer1.0-0 gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav libasound2-dev portaudio19-dev pulseaudio-utils alsa-utils psmisc ros-${ROS_DISTRO}-joint-state-publisher ros-${ROS_DISTRO}-joint-state-publisher-gui ros-${ROS_DISTRO}-robot-localization ros-${ROS_DISTRO}-robot-state-publisher ros-${ROS_DISTRO}-ros2bag ros-${ROS_DISTRO}-rosbag2-storage-default-plugins ros-${ROS_DISTRO}-rqt-tf-tree ros-${ROS_DISTRO}-rmw-fastrtps-cpp ros-${ROS_DISTRO}-rmw-cyclonedds-cpp ros-${ROS_DISTRO}-slam-toolbox ros-${ROS_DISTRO}-twist-mux ros-${ROS_DISTRO}-teleop-twist-joy ros-${ROS_DISTRO}-joy ros-${ROS_DISTRO}-usb-cam ros-${ROS_DISTRO}-xacro ros-${ROS_DISTRO}-controller-manager ros-${ROS_DISTRO}-tf-transformations ros-${ROS_DISTRO}-tf2-ros ros-${ROS_DISTRO}-tf2-tools ros-${ROS_DISTRO}-ros2-control ros-${ROS_DISTRO}-ros2-controllers ros-${ROS_DISTRO}-hardware-interface ros-${ROS_DISTRO}-joint-state-broadcaster ros-${ROS_DISTRO}-diff-drive-controller ros-${ROS_DISTRO}-mecanum-drive-controller ros-${ROS_DISTRO}-navigation2 ros-${ROS_DISTRO}-nav2-bringup ros-${ROS_DISTRO}-image-transport-plugins ros-${ROS_DISTRO}-image-view ros-${ROS_DISTRO}-rviz2 ros-${ROS_DISTRO}-foxglove-bridge ros-${ROS_DISTRO}-rtabmap-ros ros-${ROS_DISTRO}-vision-opencv ros-${ROS_DISTRO}-cv-bridge && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release && echo ${UBUNTU_CODENAME}) main" > /etc/apt/sources.list.d/gazebo-stable.list && apt-get update && apt-get install -y --no-install-recommends gz-harmonic ros-${ROS_DISTRO}-gz-ros2-control libeigen3-dev && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --break-system-packages torch torchvision torchaudio moteus-gui onnxruntime==1.19.2 numpy==1.26.4 sounddevice soundfile requests opencv-python onnx-asr espeakng-loader phonemizer-fork huggingface_hub attrs scipy tqdm certifi filelock fsspec pyyaml h5py typing-extensions && python3 -m pip install --no-cache-dir --break-system-packages --no-dependencies kokoro-onnx==0.5.0
COPY DepthVistaViewer/ /opt/depthvista/
ENV LD_LIBRARY_PATH=/opt/depthvista:/usr/local/lib:${LD_LIBRARY_PATH}
RUN printf '%s\n' '#!/usr/bin/env bash' 'cd /opt/depthvista' 'exec python3 depthvista_camera_live.py "$@"' > /usr/local/bin/depthvista && printf '%s\n' '#!/usr/bin/env bash' 'cd /opt/depthvista' 'exec python3 depthvista_view_legacy.py "$@"' > /usr/local/bin/depthvista-view && chmod +x /usr/local/bin/depthvista /usr/local/bin/depthvista-view
COPY --from=llama_builder /build/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server
COPY --from=llama_builder /build/llama.cpp/build/bin/*.so* /usr/local/lib/
RUN ldconfig
RUN git clone https://github.com/onsemi-app/cool_audio_video.git /tmp/cool_audio_video && cd /tmp/cool_audio_video && git checkout "${VLA_REF}" && VLA_FILE="$(find . -type f -name Gemma4_vla.py | head -1)" && test -n "${VLA_FILE}" && mkdir -p /opt/gemma_vla && cp -a "$(dirname "${VLA_FILE}")/." /opt/gemma_vla/
COPY GemmaVLA/patch_vla.py /tmp/patch_vla.py
RUN python3 /tmp/patch_vla.py /opt/gemma_vla/Gemma4_vla.py && rm -rf /tmp/cool_audio_video /tmp/patch_vla.py
RUN printf '%s\n' '#!/usr/bin/env bash' 'exec python3 /opt/gemma_vla/Gemma4_vla.py "$@"' > /usr/local/bin/gemma-vla-client && chmod +x /usr/local/bin/gemma-vla-client && echo 'source /opt/ros/jazzy/setup.bash' >> /etc/bash.bashrc
WORKDIR /home/onsemi/onsemi_ros/ros2_ws
CMD ["bash"]
