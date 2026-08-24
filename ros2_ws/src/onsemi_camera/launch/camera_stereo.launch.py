import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription, LaunchContext
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


package_name='onsemi_camera'

def generate_launch_description():

    camera_info = PathJoinSubstitution([ FindPackageShare("onsemi_camera"), "config", "onsemi_camera_stereo.yaml",  ])


    ld = LaunchDescription()
    camera_node = Node(
        package='usb_cam', 
        executable='usb_cam_node_exe', output='screen',
        name='onsemi_camera',
        namespace='camera',
        parameters=[camera_info],
        #remappings=camera.remappings
    )

    ld.add_action(camera_node)
    return ld



