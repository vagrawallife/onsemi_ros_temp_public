#!/usr/bin/env bash

source ./install/setup.bash >> /etc/bash.bashrc
source /opt/ros/jazzy/setup.bash >> /etc/bash.bashrc
source /home/onsemi/onsemi_mouser/ros2_ws/install/setup.bash

usbreset 2560:c128 # e-con Systems See3CAM_24CUG
ufw allow in proto udp to 224.0.0.0/4
ufw allow in proto udp from 224.0.0.0/4
export RCUTILS_COLORIZED_OUTPUT=1
bash
