
# onsemi Autonomous Mobile Robot ROS2 

Project contains the Docker setup and ros2_ws working directory.

Make sure the directory structure under onsemi_ros is not changes as the Dockerfile will use this to mount the project.
No need to install ROS2 on the host system as everything run from the docker container.


# on Host system 

- cd into onsemi_ros
- create docker image.
```

docker build -t onsemi_jazzy_amr64 ./docker/.
```
- start a container form the docker image. The contianer will be removed after stopping it.
```
./docker_amr/run_ximage.bash
```
- container will start in /home/onsemi/onsemi_ros/ros2_ws 
- run colcon to build the project
```
colcon build --symlink-install
```
- NOTE: build may stop due to dependancy error, source the workspace and re-run colcon untill colcon compleets for all packages
```
source ./install/setup.bash
```

# setup devices using udev rules   
It is needed to restart udev rules and usb hub to make see3cam, onsemi_rgb, onsemi_motor, onsemi_leds, show up in ls /dev
runs script
```
./src/onsemi_amr/startup.sh
```

# start onsemi AMR from CLI
start in simulation mode with gazibo or on hardware
```
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
```
```
ros2 launch onsemi_amr launch_robot.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
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
# video test 
'''
guvcview
```

# git help
```
git config -l
```
# start and stop links on desktop 

```
Exec=sh -c "docker stop onsemi_humble"
```
```
Exec=sh -c "cd /home/orin02/amr/; ./run_image.bash" 
```
