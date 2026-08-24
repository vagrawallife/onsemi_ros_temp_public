# ros2_onsemi_control

   *DiffBot*, or ''Differential Mobile Robot'', is a simple mobile base with differential drive.
   The robot is basically a box moving according to differential drive kinematics.

Find the documentation in [doc/userdoc.rst](doc/userdoc.rst) or on [control.ros.org](https://control.ros.org/master/doc/ros2_control_demos/example_2/doc/userdoc.html).

ros2 launch ros2_onsemi_control diffbot.launch.py
ros2 launch ros2_onsemi_control diffbot.launch.py use_mock_hardware:=True


ros2 control list_hardware_interfaces

ros2 topic pub --rate 50 /diffbot_base_controller/cmd_vel geometry_msgs/msg/TwistStamped "
twist:
  linear:
    x: 0.7
    y: 0.0
    z: 0.0
  angular:
    x: 0.0
    y: 0.0
    z: 1.0"