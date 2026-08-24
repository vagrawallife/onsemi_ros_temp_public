
# onsemi Humanoid Robot ROS2 
September 2026

This Project contains the Docker setup and ros2_ws working directory.

Make sure the directory structure under onsemi_ros is not changes as the Dockerfile will use this to mount the project.
No need to install ROS2 on the host or target system as everything runs from the docker container.
The onsemi ROS2 Autonomous Mobile Robot control application is tested on a laptop andd the following embedded system: 
* NVIDIA jetson Orin AGX,NX and Nano Development kit
* ADVANTECH MIC-711-OX3A1 NVIDIA Jetson Orin exitNX 8G Lite AI System
It is recomendded to use Visual Studio Code, This manual will describe VSC setup and usage,

# setup devices udev rules   
It is needed to prep the system outside of the container to add udev rules
```
./docker_amr/prep_host.sh
```

# Building or downloaidng the docker container

The Development workflow can be entirely on the embedded system if this has the power and tools like the
NVIDIA Jetson Orin AGX. Or it can be using a laptop / Desktop to created the docker images and run GUI
applications like rviz. A laptop can also be connected to the onsemi AMR to controll it. 
This manual will use the term host-system for an amd64 based system that can be use to create the docker image files,
and run GUI applications like rviz, foxglove, and or gazibo. 
The term emmbedde-system or target-system is used for the arm64 based system that will be integrated in the robot.   

## load the docker image 
```
$ docker pull theogony/onsemi_jazzy_arm64:latest
$ docker pull theogony/onsemi_jazzy_desktop:latest
```

## create the docker image lockaly
A docker image for the host system amd64 and or arm64 can be build.
```
docker build -t onsemi_jazzy ./docker_amr/.
```
- start a container form the docker image. The contianer will be removed after stopping it.
This will start the ddocker image source the bash files and then provide a prompt
  
```
./docker_amr/run_image.bash
./docker_amr/run_ximage.bash
```
- container will start in /home/onsemi/onsemi_ros/ros2_ws 
- run colcon to build the project

```
colcon build --symlink-install
```

# start the application
```
./src/onsemi_amr/restart.sh
```


# End ferified text instructions


- NOTE: build may stop due to dependancy error, source the workspace and re-run colcon untill colcon compleets for all packages
```
source ./install/setup.bash
```
ros2 launch hesai_ros_driver start.py

# setup devices using udev rules   
It is needed to restart udev rules and usb hub to make see3cam, onsemi_rgb, onsemi_motor, onsemi_leds, show up in ls /dev
runs script
```
./src/onsemi_amr/startup.sh
```
# test each node
ros2 launch onsemi_camera camera.launch.py 
ros2 launch onsemi_lights lights.launch.test.py 
ros2 launch teleop_twist_joy teleop-launch.py joy_config:='xbox'


# start SLAM and NAV
-Start the robot
./docker_amr/run_ximage.bash
-Start the slam toolbox
ros2 launch slam_toolbox online_async_launch.py params_file:=./src/onsemi_amr/config/mapper_params_online_async.yaml use_sim_time:=true

ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/onsemiworld.world 
ros2 launch slam_toolbox online_async_launexitm_time:=true
ros2 run nav2_util lifecycle_bringup amcl


# start onsemi AMR from CLI
start in simulation mode with gazibo or on hardware
```
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
```
```
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/onsemiworld.worl
```
```
ros2 launch onsemi_amr launch_robot.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
```
```
ros2 launch onsemi_camera camera.launch.py 
```
```
gst-launch-1.0 nvarguscamerasrc ! nvvidconv ! fpsdisplaysink
```
```
v4l2-ctl --device=/dev/video1 -L
```
```
ros2 launch onsemi_camera camera.launch.py 
```
```
ros2 run rqt_graph rqt_graph
```
```
ros2 run image_view image_view image:=/camera/image_raw
```
```
ros2 run rviz2 rviz2 -d ./src/onsemi_amr/config/amr_onsemi.rviz
```
```
python3 -c "import numpy; print(numpy.version.version)"
```
```
pip uninstall numpy
```
```
pip3 install --force-reinstall numpy==1.22.4
```
```
# packages used 
git@github.com:onsemi-app/lights_onsemi.gitcd 
git@github.com:joshnewans/serial
git@github.com:ros2/teleop_twist_joy.git
git@github.com:babakhani/rplidar_ros2.git
git@github.com:ros2/teleop_twist_joy.git


```
https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units
```
 sudo systemctl daemon-reload
 sudo systemctl enable my_robot_ros
 sudo systemctl start my_amr_bringup

create systemd file in  /lib/systemd/system . the file name is my_robot_ros.service
and copy my_amr_bringup-start and my_onsemi_arm-stop to the correct location see below.
```
# THIS IS A GENERATED FILE, NOT RECOMMENDED TO EDIT.

[Unit]
Description="bringup my_robot_ros"
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/my_amr_bringup-start
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

```
need to update docker file with pyserial for CEM102 pip install pyserial
pip install pyserial
colcon build --symlink-install
source ./install/setup.bash
ros2 launch onsemi_cem102 onsemi_cem102.launch.py 
./src/onsemi_amr/restart.sh