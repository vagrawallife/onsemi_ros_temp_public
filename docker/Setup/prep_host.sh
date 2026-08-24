#!/usr/bin/env bash


# udev rules 
sudo cp ./ros2_ws/src/onsemi_cem102/udev/onsemi_cem102.rules /etc/udev/rules.d/
sudo cp ./ros2_ws/src/onsemi_camera/udev/onsemi_cameras.rules /etc/udev/rules.d/

# runs amr_bringup for amr when xavier is booted up
sleep 2
sudo service udev reload
sleep 2
sudo service udev restart
sleep 2

bash
