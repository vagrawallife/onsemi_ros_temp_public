import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart

from launch_ros.actions import Node


package_name='onsemi_pos'
def generate_launch_description():

    ld = LaunchDescription()
    lights_node = Node(
        package= package_name,
        executable="onsemi_pos_node"
    )

    ld.add_action(lights_node)
    return ld



