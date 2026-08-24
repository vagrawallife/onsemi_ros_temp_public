clear#!/bin/bash
# this declares that current user is a sudoer



#echo "banana" | sudo -S ./docker_amr/restart_camera.bash

    #    --restart=always\
echo "Running docker..."
docker run -it --rm \
    --name=onsemi_jazzy_arm64_container \
    --mount type=bind,source="$(pwd)"/ros2_ws,target=/home/onsemi/amr_ros2/ros2_ws \
    --net=host \
    --privileged \
    --device /dev:/dev \
    --workdir=/home/onsemi/arm_ros2/ros2_ws \
    theogony/onsemi_jazzy_arm64 \
    bash


    
