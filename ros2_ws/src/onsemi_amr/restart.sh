#!/usr/bin/env bash

source ./install/setup.bash >> /etc/bash.bashrc
source /opt/ros/jazzy/setup.bash >> /etc/bash.bashrc
#source /home/onsemi/onsemi_ros/ros2_ws/install/setup.bash
source /home/nvidia/Documents/onsemi_ros/ros2_ws/install/setup.bash

export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/jazzy/lib/
export GZ_SIM_RESOURCE_PATH=/opt/ros/jazzy/opt/gz_sim_vendor/share/gz/gz-sim8/

#usbreset 2560:c128 # e-con Systems See3CAM_24CUG
#ufw allow in proto udp to 224.0.0.0/4
#ufw allow in proto udp from 224.0.0.0/4

export RCUTILS_COLORIZED_OUTPUT=1
ros2 launch onsemi_amr launch_robo.launch.py 
#ros2 launch onsemi_amr launch_swir.launch.py 

#bash
