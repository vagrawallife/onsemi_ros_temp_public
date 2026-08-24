import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart

from launch_ros.actions import Node


package_name='onsemi_cem102'
def generate_launch_description():

    ld = LaunchDescription()
    cem102_node = Node(
        package= package_name,
        executable="onsemi_cem102_node"
    )

    ld.add_action(cem102_node)
    return ld



