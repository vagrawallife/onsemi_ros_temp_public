## Simulation first

##install Gazebo on the host system follow
https://gazebosim.org/docs/harmonic/install_ubuntu/

sudo apt-get install mesa-utils
sudo ufw allow in proto udp to 224.0.0.0/4
sudo ufw allow in proto udp from 224.0.0.0/4
sudo apt-get install dbus-x11
export QT_QPA_PLATFORM=xcb
gz sim -v 4 ./empty.world 



## Robot Package Template
'''

ros2 launch slam_toolbox online_async_launch.py slam_params_file:=/home/onsemi/onsemi_ros/ros2_ws/src/onsemi_amr/config/mapper_params_online_async.yaml use_sim_time:=true

ros2 launch onsemi_amr navigation_launch.py sim_mode:=true
'''

ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/corridor.world



ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/onsemiworld.world 
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/table.world 
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/small_warehouse.world 
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/corridor.world
ros2 launch onsemi_amr launch_sim.launch.py world:=src/onsemi_amr/worlds/myworld.world

ros2 launch onsemi_amr launch_robot.launch.py world:=src/onsemi_amr/worlds/obstacles.world 
ros2 launch gazebo_ros gazebo.launch.py



ros2 launch onsemi_amr launch_robot.launch.py world:=src/onsemi_amr/worlds/myworld.world 

ros2 launch onsemi_camera camera.launch.py

ros2 run camera_calibration cameracalibrator --size 8x6 --square 0.030 --ros-args --remap image:=/camera/image_raw --ros-args --remapcamera:=/camera


ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diff_drive_controller/cmd_vel_unstamped

ros2 run rviz2 rviz2 -d src/onsemi_amr/config/main.rviz --ros-args -p use_sim_time:=true

ros2 launch onsemi_amr ball_tracker.launch.py sim_mode:=true


ros2 run image_transport republish compressed raw --ros-args -r in/compressed:=/image_raw/compressed -r out:=/image_raw/uncompressed
ros2 launch onsemi_amr ball_tracker.launch.py tune_detection:=true detect_only:=true image_topic:=/camera/image_raw sim_time:=true
ros2 launch onsemi_amr ball_tracker.launch.py sim_time:=true

ros2 launch onsemi_amr ball_tracker.launch.py tune_detection:=true detect_only:=true sim_time:=true

docker exec -it onsemi_noetic batch
ros2 run rqt_image_view rqt_image_view


ros2 run ball_tracker detect_ball --ros-args -p tuning_mode:=true image_in:=image_raw
ros2 launch slam_toolbox online_async_launch.py params_file:=./src/onsemi_amr/config/mapper_params_online_async.yaml
ros2 launch onsemi_amr navigation_launch.py sim_mode:=true
ros2 launch onsemi_amr online_async_launch.py sim_mode:=true
ros2 launch onsemi_amr localization_launch.py map:=./src/onsemi_amr/maps/corridor_save.yaml sim_mode:=false

ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=./corridor_save.yaml -p use_sim_time:=true
ros2 run nav2_util lifecycle_bringup map_server
ros2 run nav2_amcl amcl --ros-args -p use_sim_time:=true
ros2 run nav2_util lifecycle_bringup amcl

ros2 run joy joy_node
ros2 run joy_tester test_joy
ros2 launch onsemi_amr joystick.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/diffbot_base_controller/cmd_vel

# display node connections
rqt_graph

ros2 topic pub --rate 50 /diff_cont/cmd_vel_unstamped geometry_msgs/msg/TwistStamped "
twist:
  linear:
    x: 0.7
    y: 0.0
    z: 0.0
  angular:
    x: 0.0
    y: 0.0
    z: 1.0"